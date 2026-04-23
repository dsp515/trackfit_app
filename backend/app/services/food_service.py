import base64
import io
import json
import os
from datetime import date, datetime

import httpx
from PIL import Image
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.food_log import FoodLog
from app.models.daily_stats import DailyStats
from app.schemas.food import FoodLogCreate, TodayFoodSummary


class FoodService:
    def __init__(self, db: Session):
        self.db = db
        self.food_db: dict = {}
        try:
            with open(settings.FOOD_DB_PATH, encoding="utf-8") as f:
                self.food_db = json.load(f)
        except (FileNotFoundError, UnicodeDecodeError):
            pass

        # CNN model for food recognition (loaded lazily)
        self._model = None
        self._classes = None
        self._transform = None

    def _decode_base64_image(self, image_base64: str) -> Image.Image:
        """Decode raw base64 or data-URL image into an RGB PIL image."""
        raw = image_base64.strip()
        if raw.startswith("data:image") and "," in raw:
            raw = raw.split(",", 1)[1]

        # Some clients omit base64 padding; restore it before decoding.
        missing_padding = len(raw) % 4
        if missing_padding:
            raw += "=" * (4 - missing_padding)

        image_data = base64.b64decode(raw)
        return Image.open(io.BytesIO(image_data)).convert("RGB")

    def _load_recognition_model(self):
        """Lazily load the PyTorch food recognition model if available."""
        if self._model is not None:
            return
        try:
            import torch
            import torchvision.transforms as transforms

            model_path = settings.FOOD_MODEL_PATH
            classes_path = settings.FOOD_CLASSES_PATH
            
            if not os.path.exists(classes_path):
                # Default demo classes for final year project demonstration
                self._classes = [
                    "apple", "banana", "orange", "grapes", "mango",
                    "bread", "rice", "pasta", "chicken", "beef",
                    "egg", "milk", "yogurt", "cheese", "butter",
                    "pizza", "burger", "fries", "salad", "soup",
                    "cake", "cookie", "chocolate", "ice_cream", "coffee"
                ]
            else:
                with open(classes_path) as f:
                    self._classes = json.load(f)

            if not os.path.exists(model_path):
                # Demo mode: Use pre-trained ResNet for demonstration
                from torchvision import models as tv_models
                self._model = tv_models.resnet18(weights="IMAGENET1K_V1")
                self._model.fc = torch.nn.Linear(
                    self._model.fc.in_features, len(self._classes)
                )
                self._model.eval()
            else:
                from torchvision import models as tv_models
                self._model = tv_models.resnet18(weights=None)
                self._model.fc = torch.nn.Linear(
                    self._model.fc.in_features, len(self._classes)
                )
                self._model.load_state_dict(
                    torch.load(model_path, map_location="cpu")
                )
                self._model.eval()
            
            self._transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                ),
            ])
        except Exception:
            self._model = None

    # ─── Search ────────────────────────────────────────────────

    def search_foods(
        self, query: str, cuisine: str | None = None, limit: int = 20
    ) -> list[dict]:
        query_lower = query.lower()
        results = []
        for key, item in self.food_db.items():
            if cuisine:
                item_cuisine = item.get("cuisine_region", "").lower()
                if cuisine.lower() not in item_cuisine:
                    continue
            name = item.get("name", "").lower()
            aliases = [a.lower() for a in item.get("common_aliases", [])]
            if query_lower in name or any(query_lower in a for a in aliases):
                results.append({
                    "food_key": key,
                    "name": item["name"],
                    "calories": item.get("calories", 0),
                    "protein_g": item.get("protein_g", 0),
                    "carbs_g": item.get("carbs_g", 0),
                    "fats_g": item.get("fats_g", 0),
                    "fiber_g": item.get("fiber_g", 0),
                    "typical_portion_g": item.get("typical_portion_g", 100),
                    "is_veg": item.get("is_veg", True),
                    "category": item.get("category", "Other"),
                })
                if len(results) >= limit:
                    break
        return results

    def get_food_by_key(self, food_key: str) -> dict | None:
        return self.food_db.get(food_key)

    # ─── CNN Food Recognition ──────────────────────────────────

    def recognize_food(self, image_base64: str) -> dict:
        """Run CNN on a food image and return top-5 predictions from food DB."""
        self._load_recognition_model()
        if not self._model or not self._classes:
            return {
                "error": "Food recognition model not loaded",
                "predictions": [],
                "hint": "Place food_model.pt and food_classes.json in backend/app/models/",
            }

        import torch

        try:
            img = self._decode_base64_image(image_base64)
            img_tensor = self._transform(img).unsqueeze(0)
        except Exception as e:
            return {"error": f"Invalid image: {e}", "predictions": []}

        with torch.no_grad():
            output = self._model(img_tensor)
            probs = torch.softmax(output[0], dim=0)
            top5 = torch.topk(probs, min(5, len(self._classes)))

        predictions = []
        for i in range(len(top5.indices)):
            idx = top5.indices[i].item()
            food_key = self._classes[idx]
            confidence = round(top5.values[i].item(), 4)
            item = self.food_db.get(food_key)
            if item:
                predictions.append({
                    "food_key": food_key,
                    "name": item["name"],
                    "confidence": confidence,
                    "calories": item.get("calories", 0),
                    "protein_g": item.get("protein_g", 0),
                    "carbs_g": item.get("carbs_g", 0),
                    "fats_g": item.get("fats_g", 0),
                    "typical_portion_g": item.get("typical_portion_g", 100),
                    "is_veg": item.get("is_veg", True),
                })

        return {"predictions": predictions}

    # ─── ViT Food Recognition (from app.py) ─────────────────────

    def recognize_food_vit(self, image_base64: str) -> dict:
        """Identify food using Google ViT model + get nutrition from API Ninjas.
        
        This is the approach from app.py:
        1. ViT classifies the food image -> food name
        2. API Ninjas nutrition API -> calories, protein, carbs, fat
        """
        try:
            from transformers import ViTImageProcessor, ViTForImageClassification
            import torch
        except ImportError:
            return {
                "error": "transformers library not installed. Run: pip install transformers torch",
                "predictions": [],
                "source": "vit_unavailable",
            }

        try:
            img = self._decode_base64_image(image_base64)
        except Exception as e:
            return {"error": f"Invalid image: {e}", "predictions": []}

        # Load ViT model (cached after first call)
        if not hasattr(self, '_vit_model'):
            model_name = "google/vit-base-patch16-224"
            hf_token = settings.HF_TOKEN or None
            try:
                self._vit_extractor = ViTImageProcessor.from_pretrained(
                    model_name,
                    token=hf_token,
                )
                self._vit_model = ViTForImageClassification.from_pretrained(
                    model_name,
                    token=hf_token,
                )
            except Exception as e:
                return {
                    "error": f"Vision model unavailable: {e}",
                    "predictions": [],
                    "source": "vit_unavailable",
                    "hint": "Set HF_TOKEN env var for hosted Vision Transformer access.",
                }

        # Classify
        try:
            inputs = self._vit_extractor(images=img, return_tensors="pt")
            with torch.no_grad():
                outputs = self._vit_model(**inputs)
                probs = torch.softmax(outputs.logits[0], dim=0)
                top5 = torch.topk(probs, 5)
        except Exception as e:
            return {
                "error": f"Food recognition failed: {e}",
                "predictions": [],
                "source": "vit_error",
            }

        predictions = []
        for i in range(len(top5.indices)):
            idx = top5.indices[i].item()
            label = self._vit_model.config.id2label[idx]
            food_name = label.split(',')[0].strip()
            confidence = round(top5.values[i].item(), 4)
            predictions.append({
                "food_name": food_name,
                "confidence": confidence,
            })

        # Get nutrition for top prediction via API Ninjas
        top_food = predictions[0]["food_name"] if predictions else None
        nutrition = None
        if top_food and settings.API_NINJAS_KEY:
            nutrition = self._fetch_api_ninjas_nutrition(top_food)

        return {
            "predictions": predictions,
            "top_food": top_food,
            "nutrition": nutrition,
            "source": "vit",
        }

    def _fetch_api_ninjas_nutrition(self, food_name: str) -> dict | None:
        """Fetch nutrition data from API Ninjas (from app.py get_calories)."""
        try:
            resp = httpx.get(
                f"https://api.api-ninjas.com/v1/nutrition?query={food_name}",
                headers={"X-Api-Key": settings.API_NINJAS_KEY},
                timeout=10.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    item = data[0]
                    return {
                        "name": item.get("name", food_name),
                        "calories": item.get("calories", 0),
                        "protein_g": item.get("protein_g", 0),
                        "carbs_g": item.get("carbohydrates_total_g", 0),
                        "fat_g": item.get("fat_total_g", 0),
                        "fiber_g": item.get("fiber_g", 0),
                        "sugar_g": item.get("sugar_g", 0),
                        "sodium_mg": item.get("sodium_mg", 0),
                        "serving_size_g": item.get("serving_size_g", 100),
                    }
        except Exception:
            pass
        return None

    # ─── Barcode Lookup ────────────────────────────────────────

    async def barcode_lookup(self, barcode: str) -> dict:
        """Look up a product by barcode via Open Food Facts API."""
        normalized_barcode = "".join(ch for ch in barcode if ch.isdigit())
        if len(normalized_barcode) < 8 or len(normalized_barcode) > 14:
            return {
                "found": False,
                "error": "Invalid barcode. Must be 8-14 digits.",
            }

        headers = {
            "User-Agent": "TrackFitUltra/1.0 (support: trackfit app)",
            "Accept": "application/json",
        }
        urls = [
            f"https://world.openfoodfacts.org/api/v2/product/{normalized_barcode}.json",
            f"https://world.openfoodfacts.org/api/v0/product/{normalized_barcode}.json",
        ]

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                data = None
                last_status = None
                for url in urls:
                    resp = await client.get(
                        url,
                        headers=headers,
                        follow_redirects=True,
                    )
                    last_status = resp.status_code
                    if resp.status_code == 200:
                        data = resp.json()
                        break

                if data is None:
                    if last_status == 429:
                        return {
                            "found": False,
                            "error": "Barcode service is busy right now. Please try again shortly.",
                        }
                    return {
                        "found": False,
                        "error": f"API request failed (status {last_status})",
                    }

                if data.get("status") != 1:
                    return {"found": False, "error": "Product not found"}

                product = data["product"]
                nutriments = product.get("nutriments", {})

                def get_float(key: str) -> float:
                    value = nutriments.get(key, 0)
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        return 0.0

                return {
                    "found": True,
                    "barcode": normalized_barcode,
                    "name": product.get("product_name", "Unknown"),
                    "brand": product.get("brands", ""),
                    "image_url": product.get("image_front_small_url", ""),
                    "calories_per_100g": get_float("energy-kcal_100g"),
                    "protein_per_100g": get_float("proteins_100g"),
                    "carbs_per_100g": get_float("carbohydrates_100g"),
                    "fat_per_100g": get_float("fat_100g"),
                    "fiber_per_100g": get_float("fiber_100g"),
                    "sugar_per_100g": get_float("sugars_100g"),
                    "sodium_per_100g": get_float("sodium_100g"),
                    "serving_size": product.get("serving_size", "100g"),
                    "nutriscore_grade": product.get("nutriscore_grade", ""),
                }
        except Exception as e:
            return {"found": False, "error": str(e)}

    # ─── Log Food ──────────────────────────────────────────────

    def log_food(self, user_id: str, food_data: FoodLogCreate) -> FoodLog:
        if food_data.food_key and food_data.food_key in self.food_db:
            db_item = self.food_db[food_data.food_key]
            portion = db_item.get("typical_portion_g", 100)
            ratio = food_data.amount_g / portion if portion > 0 else 1
            log = FoodLog(
                user_id=user_id,
                name=db_item["name"],
                calories=int(db_item.get("calories", 0) * ratio),
                protein=round(db_item.get("protein_g", 0) * ratio, 1),
                carbs=round(db_item.get("carbs_g", 0) * ratio, 1),
                fat=round(db_item.get("fats_g", 0) * ratio, 1),
                fiber=round(db_item.get("fiber_g", 0) * ratio, 1),
                sugar=round(db_item.get("sugar_g", 0) * ratio, 1),
                sodium=int(db_item.get("sodium_mg", 0) * ratio),
                amount_g=food_data.amount_g,
                meal_type=food_data.meal_type,
            )
        else:
            log = FoodLog(
                user_id=user_id,
                name=food_data.name,
                calories=food_data.calories,
                protein=food_data.protein,
                carbs=food_data.carbs,
                fat=food_data.fat,
                fiber=food_data.fiber,
                sugar=food_data.sugar,
                sodium=food_data.sodium,
                amount_g=food_data.amount_g,
                meal_type=food_data.meal_type,
            )

        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        self._update_daily_stats(user_id)
        return log

    def get_today_logs(self, user_id: str) -> TodayFoodSummary:
        today = date.today()
        logs = (
            self.db.query(FoodLog)
            .filter(
                FoodLog.user_id == user_id,
                FoodLog.logged_at >= datetime(today.year, today.month, today.day),
            )
            .order_by(FoodLog.logged_at.desc())
            .all()
        )

        by_meal: dict[str, list] = {
            "breakfast": [], "lunch": [], "dinner": [], "snacks": [],
        }
        total_cal = total_protein = total_carbs = total_fat = total_fiber = 0

        for log in logs:
            meal = log.meal_type.lower()
            if meal not in by_meal:
                by_meal[meal] = []
            by_meal[meal].append(log)
            total_cal += log.calories
            total_protein += log.protein
            total_carbs += log.carbs
            total_fat += log.fat
            total_fiber += (log.fiber or 0)

        return TodayFoodSummary(
            total_calories=total_cal,
            total_protein=round(total_protein, 1),
            total_carbs=round(total_carbs, 1),
            total_fat=round(total_fat, 1),
            total_fiber=round(total_fiber, 1),
            logs=logs,
            by_meal=by_meal,
        )

    def delete_food_log(self, log_id: str, user_id: str) -> bool:
        log = (
            self.db.query(FoodLog)
            .filter(FoodLog.id == log_id, FoodLog.user_id == user_id)
            .first()
        )
        if not log:
            return False
        self.db.delete(log)
        self.db.commit()
        self._update_daily_stats(user_id)
        return True

    def _update_daily_stats(self, user_id: str):
        today = date.today()
        summary = self.get_today_logs(user_id)
        stat = (
            self.db.query(DailyStats)
            .filter(DailyStats.user_id == user_id, DailyStats.date == today)
            .first()
        )
        if not stat:
            stat = DailyStats(user_id=user_id, date=today)
            self.db.add(stat)

        stat.calories_consumed = summary.total_calories
        stat.protein_g = summary.total_protein
        stat.carbs_g = summary.total_carbs
        stat.fat_g = summary.total_fat
        self.db.commit()
