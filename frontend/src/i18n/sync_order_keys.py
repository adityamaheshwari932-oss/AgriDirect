"""Sync newly added keys for direct order creation and order photos across all 23 locales."""

import json
from pathlib import Path

LOCALES_DIR = Path(__file__).parent / "locales"

# English base translations
ORDERS_NEW_KEYS = {
    "place_direct_order": "Place Purchase Order",
    "direct_order_subtitle": "Direct purchase with instant inventory reservation",
    "order_quantity": "Order Volume",
    "estimated_total": "Estimated Total Amount",
    "target_delivery_date": "Target Delivery Date",
    "delivery_address": "Delivery Address",
    "enter_delivery_address": "Warehouse dock / Receiving point",
    "handling_instructions": "Special Handling & Delivery Instructions",
    "notes_placeholder": "e.g., Crate packaging, morning delivery slot, inspection contact person",
    "attach_reference_photos": "Order Quality Evidence & Reference Photos",
    "images_count": "photos",
    "supported_image_types": "Attach specifications, quality requirements, or purchase documents (JPEG, PNG, WebP ≤ 5 MB).",
    "placing_order": "Placing Order...",
    "confirm_and_place_order": "Confirm & Place Order",
    "order_placed_success": "Purchase order placed successfully!",
    "order_placement_failed": "Failed to place order.",
    "max_images_limit": "You can attach a maximum of 5 images per order.",
    "file_too_large": "Each image must not exceed 5 MB.",
    "unsupported_format": "Only JPEG, PNG, and WebP images are permitted.",
}

ORDERS_DETAIL_NEW_KEYS = {
    "order_photographs": "Order Documentation & Quality Photographs",
    "photos_attached": "photos attached",
}

MARKETPLACE_NEW_KEYS = {
    "place_direct_order": "Place Order",
}

# Indic translations for Hindi
HI_ORDERS_KEYS = {
    "place_direct_order": "खरीद आदेश दें",
    "direct_order_subtitle": "तत्काल इन्वेंट्री आरक्षण के साथ सीधी खरीद",
    "order_quantity": "आदेश मात्रा",
    "estimated_total": "अनुमानित कुल राशि",
    "target_delivery_date": "लक्षित वितरण तिथि",
    "delivery_address": "वितरण का पता",
    "enter_delivery_address": "गोदाम डॉक / प्राप्ति बिंदु",
    "handling_instructions": "विशेष हैंडलिंग और वितरण निर्देश",
    "notes_placeholder": "उदा., क्रेट पैकेजिंग, सुबह का डिलीवरी स्लॉट, निरीक्षण संपर्क व्यक्ति",
    "attach_reference_photos": "ऑर्डर गुणवत्ता साक्ष्य और संदर्भ तस्वीरें",
    "images_count": "तस्वीरें",
    "supported_image_types": "विनिर्देश, गुणवत्ता आवश्यकताएं या खरीद दस्तावेज संलग्न करें (JPEG, PNG, WebP ≤ 5 MB)।",
    "placing_order": "आदेश दिया जा रहा है...",
    "confirm_and_place_order": "पुष्टि करें और आदेश दें",
    "order_placed_success": "खरीद आदेश सफलतापूर्वक दिया गया!",
    "order_placement_failed": "आदेश देने में विफल।",
    "max_images_limit": "आप प्रति ऑर्डर अधिकतम 5 तस्वीरें संलग्न कर सकते हैं।",
    "file_too_large": "प्रत्येक तस्वीर 5 MB से अधिक नहीं होनी चाहिए।",
    "unsupported_format": "केवल JPEG, PNG और WebP तस्वीरों की अनुमति है।",
}

HI_ORDERS_DETAIL_KEYS = {
    "order_photographs": "आदेश दस्तावेज और गुणवत्ता तस्वीरें",
    "photos_attached": "तस्वीरें संलग्न",
}

HI_MARKETPLACE_KEYS = {
    "place_direct_order": "आदेश दें",
}

LANGUAGES = [
    "as", "bn", "brx", "doi", "en", "gu", "hi", "kn", "kok", "ks",
    "mai", "ml", "mni", "mr", "ne", "or", "pa", "sa", "sat", "sd",
    "ta", "te", "ur"
]

def sync_keys():
    for lang in LANGUAGES:
        orders_file = LOCALES_DIR / lang / "orders.json"
        if orders_file.exists():
            with open(orders_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            source_keys = HI_ORDERS_KEYS if lang == "hi" else ORDERS_NEW_KEYS
            source_detail = HI_ORDERS_DETAIL_KEYS if lang == "hi" else ORDERS_DETAIL_NEW_KEYS

            for k, v in source_keys.items():
                if k not in data:
                    data[k] = v

            if "detail" in data and isinstance(data["detail"], dict):
                for k, v in source_detail.items():
                    if k not in data["detail"]:
                        data["detail"][k] = v

            with open(orders_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        mkt_file = LOCALES_DIR / lang / "marketplace.json"
        if mkt_file.exists():
            with open(mkt_file, "r", encoding="utf-8") as f:
                mkt_data = json.load(f)

            source_mkt = HI_MARKETPLACE_KEYS if lang == "hi" else MARKETPLACE_NEW_KEYS
            for k, v in source_mkt.items():
                if k not in mkt_data:
                    mkt_data[k] = v

            with open(mkt_file, "w", encoding="utf-8") as f:
                json.dump(mkt_data, f, ensure_ascii=False, indent=2)

    print("Synced direct order & image localization keys across all 23 languages successfully.")

if __name__ == "__main__":
    sync_keys()
