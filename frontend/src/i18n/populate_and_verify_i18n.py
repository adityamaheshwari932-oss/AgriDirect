"""Script to populate and strictly verify 23-language localization parity for Product Image feature.

Keys populated:
- dashboard.json (29 keys)
- errors.json (8 keys)
- marketplace.json (3 keys)
Total: 40 keys per language across all 23 official Indian languages supported by AgriDirect.
"""

import json
from pathlib import Path
import sys

LOCALES_DIR = Path(__file__).parent / "locales"

# Translations dictionary for the 21 languages (en & hi already have them)
TRANSLATIONS = {
    "mr": {
        "dashboard": {
            "produce_photos_title": "शेतमाल लॉटची छायाचित्रे",
            "photo_limits_guidance": "कमाल १० छायाचित्रे, प्रत्येकी ५ MB (JPEG, PNG, WebP)",
            "current_photos_label": "सध्याची छायाचित्रे:",
            "make_primary_photo": "मुख्य छायाचित्र बनवा",
            "primary_photo_badge": "मुख्य",
            "photos_to_upload_label": "अपलोड करावयाची छायाचित्रे:",
            "set_primary": "मुख्य सेट करा",
            "add_first_photos": "कापणीची छायाचित्रे निवडा किंवा काढा",
            "add_more_photos": "आणखी छायाचित्रे जोडा ({{remaining}} शिल्लक)",
            "confirm_delete_photo": "तुम्हाला खरोखर हे छायाचित्र या सूचीमधून काढायचे आहे का?",
            "image_uploaded_success": "छायाचित्रे यशस्वीरीत्या अपलोड केली.",
            "image_deleted_success": "छायाचित्र यशस्वीरीत्या हटवले.",
            "primary_thumbnail_updated": "मुख्य कॅटलॉग लघुप्रतिमा अद्ययावत केली.",
            "reorder_success": "छायाचित्रांचा क्रम अद्ययावत केला.",
            "manage_photos_title": "शेतमाल छायाचित्रे व्यवस्थापित करा",
            "photos_attached_count": "{{count}}/{{max}} छायाचित्रे जोडली",
            "attached_photos_heading": "जोडलेली शेतमाल छायाचित्रे ({{count}}/{{max}})",
            "no_photos_yet": "अद्याप कोणतीही छायाचित्रे जोडलेली नाहीत",
            "upload_photos_hint": "व्यावसायिक खरेदीदारांना आकर्षित करण्यासाठी आपल्या उत्पादित मालाची स्पष्ट छायाचित्रे अपलोड करा.",
            "primary_thumbnail": "मुख्य लघुप्रतिमा",
            "make_primary": "मुख्य बनवा",
            "catalog_display_photo": "कॅटलॉग प्रदर्शन छायाचित्र",
            "move_earlier": "मागे हलवा",
            "move_later": "पुढे हलवा",
            "delete_photo": "छायाचित्र हटवा",
            "upload_new_photo": "नवीन छायाचित्र(े) अपलोड करा",
            "set_as_primary": "मुख्य म्हणून सेट करा",
            "image_spec_hint": "एकूण कमाल १० छायाचित्रे • प्रत्येकी ५ MB • JPEG, PNG किंवा WebP",
            "upload_photo_btn": "छायाचित्र(े) अपलोड करा"
        },
        "errors": {
            "image_limit_reached": "प्रति सूची कमाल १० छायाचित्रांची मर्यादा संपली आहे.",
            "image_size_exceeded": "छायाचित्राचा आकार ५ MB च्या मर्यादेपेक्षा जास्त आहे.",
            "unsupported_image_format": "असमर्थित प्रतिमा स्वरूप. कृपया JPEG, PNG किंवा WebP छायाचित्र निवडा.",
            "select_image_first": "कृपया अपलोड करण्यासाठी छायाचित्र निवडा.",
            "upload_failed": "छायाचित्र अपलोड अयशस्वी झाले. कृपया पुन्हा प्रयत्न करा.",
            "network_error_upload": "छायाचित्र अपलोड करताना अनपेक्षित नेटवर्क त्रुटी आली.",
            "delete_failed": "छायाचित्र हटवण्यात अयशस्वी.",
            "primary_failed": "मुख्य छायाचित्र नियुक्त करण्यात अयशस्वी."
        },
        "marketplace": {
            "catalog_primary_photo": "कॅटलॉग मुख्य छायाचित्र",
            "thumbnail_n": "लघुप्रतिमा {{n}}",
            "no_photos_uploaded": "या शेतमाल लॉटसाठी कोणतीही छायाचित्रे अपलोड केलेली नाहीत"
        }
    },
    "gu": {
        "dashboard": {
            "produce_photos_title": "ઉપજ લૉટના ફોટોગ્રાફ્સ",
            "photo_limits_guidance": "મહત્તમ ૧૦ ફોટા, દરેક ૫ MB (JPEG, PNG, WebP)",
            "current_photos_label": "હાલના ફોટોગ્રાફ્સ:",
            "make_primary_photo": "મુખ્ય ફોટો બનાવો",
            "primary_photo_badge": "મુખ્ય",
            "photos_to_upload_label": "અપલોડ કરવાના ફોટોગ્રાફ્સ:",
            "set_primary": "મુખ્ય સેટ કરો",
            "add_first_photos": "પાકના ફોટા પસંદ કરો અથવા લો",
            "add_more_photos": "વધુ ફોટા ઉમેરો ({{remaining}} બાકી)",
            "confirm_delete_photo": "શું તમે ખરેખર આ સૂચિમાંથી આ ફોટો દૂર કરવા માંગો છો?",
            "image_uploaded_success": "ફોટોગ્રાફ્સ સફળતાપૂર્વક અપલોડ થયા.",
            "image_deleted_success": "ફોટો સફળતાપૂર્વક કાઢી નાખ્યો.",
            "primary_thumbnail_updated": "મુખ્ય કેટલોગ થંબનેલ અપડેટ કરવામાં આવ્યું.",
            "reorder_success": "ફોટો ડિસ્પ્લે ક્રમ અપડેટ કર્યો.",
            "manage_photos_title": "ઉપજ ફોટા મેનેજ કરો",
            "photos_attached_count": "{{count}}/{{max}} ફોટા જોડાયેલા છે",
            "attached_photos_heading": "જોડાયેલ ઉપજ ફોટા ({{count}}/{{max}})",
            "no_photos_yet": "હજી સુધી કોઈ ફોટા જોડાયા નથી",
            "upload_photos_hint": "વાણિજ્યિક ખરીદદારોને આકર્ષવા માટે તમારા પાકના સ્પષ્ટ ફોટા અપલોડ કરો.",
            "primary_thumbnail": "મુખ્ય થંબનેલ",
            "make_primary": "મુખ્ય બનાવો",
            "catalog_display_photo": "કેટલોગ ડિસ્પ્લે ફોટો",
            "move_earlier": "પહેલાં ખસેડો",
            "move_later": "પછી ખસેડો",
            "delete_photo": "ફોટો કાઢી નાખો",
            "upload_new_photo": "નવો ફોટો અપલોડ કરો",
            "set_as_primary": "મુખ્ય તરીકે સેટ કરો",
            "image_spec_hint": "કુલ મહત્તમ ૧૦ ફોટા • દરેક ૫ MB • JPEG, PNG અથવા WebP",
            "upload_photo_btn": "ફોટો અપલોડ કરો"
        },
        "errors": {
            "image_limit_reached": "સૂચિ દીઠ મહત્તમ ૧૦ ફોટાની મર્યાદા પહોંચી ગઈ છે.",
            "image_size_exceeded": "ફોટોનું કદ ૫ MB મર્યાદા કરતાં વધી ગયું છે.",
            "unsupported_image_format": "અસમર્થિત ઇમેજ ફોર્મેટ. કૃપા કરીને JPEG, PNG અથવા WebP ફોટો પસંદ કરો.",
            "select_image_first": "કૃપા કરીને અપલોડ કરવા માટે ફોટો ફાઇલ પસંદ કરો.",
            "upload_failed": "ફોટો અપલોડ કરવામાં નિષ્ફળ. કૃપા કરીને ફરી પ્રયાસ કરો.",
            "network_error_upload": "ફોટો અપલોડ કરતી વખતે નેટવર્ક ભૂલ આવી.",
            "delete_failed": "ફોટો કાઢી નાખવામાં નિષ્ફળ.",
            "primary_failed": "મુખ્ય ઇમેજ નિયુક્ત કરવામાં નિષ્ફળ."
        },
        "marketplace": {
            "catalog_primary_photo": "કેટલોગ મુખ્ય ફોટો",
            "thumbnail_n": "થંબનેલ {{n}}",
            "no_photos_uploaded": "આ પાક માટે કોઈ ફોટોગ્રાફ અપલોડ કરવામાં આવ્યા નથી"
        }
    },
    "bn": {
        "dashboard": {
            "produce_photos_title": "ফসলের লটের আলোকচিত্র",
            "photo_limits_guidance": "সর্বোচ্চ ১০টি ছবি, প্রতিটি ৫ MB (JPEG, PNG, WebP)",
            "current_photos_label": "বিদ্যমান ছবি:",
            "make_primary_photo": "প্রধান ছবি করুন",
            "primary_photo_badge": "প্রধান",
            "photos_to_upload_label": "আপলোড করার ছবি:",
            "set_primary": "প্রধান হিসেবে নির্ধারণ করুন",
            "add_first_photos": "ফসলের ছবি নির্বাচন করুন বা তুলুন",
            "add_more_photos": "আরও ছবি যোগ করুন ({{remaining}}টি বাকি)",
            "confirm_delete_photo": "আপনি কি নিশ্চিতভাবে এই তালিকা থেকে এই ছবিটি সরাতে চান?",
            "image_uploaded_success": "ছবি সফলভাবে আপলোড হয়েছে।",
            "image_deleted_success": "ছবি সফলভাবে মুছে ফেলা হয়েছে।",
            "primary_thumbnail_updated": "প্রধান ক্যাটালগ থাম্বনেইল আপডেট করা হয়েছে।",
            "reorder_success": "ছবির প্রদর্শনের ক্রম আপডেট করা হয়েছে।",
            "manage_photos_title": "ফসলের ছবি পরিচালনা করুন",
            "photos_attached_count": "{{count}}/{{max}}টি ছবি সংযুক্ত",
            "attached_photos_heading": "সংযুক্ত ফসলের ছবি ({{count}}/{{max}})",
            "no_photos_yet": "এখনও কোনো ছবি সংযুক্ত করা হয়নি",
            "upload_photos_hint": "বাণিজ্যিক ক্রেতাদের আকৃষ্ট করতে আপনার কাটা ফসলের স্পষ্ট ছবি আপলোড করুন।",
            "primary_thumbnail": "প্রধান থাম্বনেইল",
            "make_primary": "প্রধান করুন",
            "catalog_display_photo": "ক্যাটালগ প্রদর্শন ছবি",
            "move_earlier": "আগে সরান",
            "move_later": "পরে সরান",
            "delete_photo": "ছবি মুছুন",
            "upload_new_photo": "নতুন ছবি আপলোড করুন",
            "set_as_primary": "প্রধান হিসেবে সেট করুন",
            "image_spec_hint": "সর্বমোট ১০টি ছবি • প্রতিটি ৫ MB • JPEG, PNG বা WebP",
            "upload_photo_btn": "ছবি আপলোড করুন"
        },
        "errors": {
            "image_limit_reached": "প্রতি তালিকায় সর্বোচ্চ ১০টি ছবির সীমা পূর্ণ হয়েছে।",
            "image_size_exceeded": "ছবির আকার ৫ MB সীমা ছাড়িয়ে গেছে।",
            "unsupported_image_format": "অসমর্থিত ছবির বিন্যাস। অনুগ্রহ করে JPEG, PNG বা WebP ছবি নির্বাচন করুন।",
            "select_image_first": "অনুগ্রহ করে আপলোড করার জন্য একটি ছবি ফাইল নির্বাচন করুন।",
            "upload_failed": "ছবি আপলোড ব্যর্থ হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।",
            "network_error_upload": "ছবি আপলোড করার সময় নেটওয়ার্ক ত্রুটি ঘটেছে।",
            "delete_failed": "ছবি মুছতে ব্যর্থ হয়েছে।",
            "primary_failed": "প্রধান ছবি নির্ধারণ করতে ব্যর্থ হয়েছে।"
        },
        "marketplace": {
            "catalog_primary_photo": "ক্যাটালগের প্রধান ছবি",
            "thumbnail_n": "থাম্বনেইল {{n}}",
            "no_photos_uploaded": "এই ফসলের লটের জন্য কোনো ছবি আপলোড করা হয়নি"
        }
    },
    "ta": {
        "dashboard": {
            "produce_photos_title": "விளைபொருள் தொகுப்பு புகைப்படங்கள்",
            "photo_limits_guidance": "அதிகபட்சம் 10 படங்கள், தலா 5 MB (JPEG, PNG, WebP)",
            "current_photos_label": "தற்போதுள்ள புகைப்படங்கள்:",
            "make_primary_photo": "முதன்மை புகைப்படமாக்கு",
            "primary_photo_badge": "முதன்மை",
            "photos_to_upload_label": "பதிவேற்ற வேண்டிய புகைப்படங்கள்:",
            "set_primary": "முதன்மை என அமை",
            "add_first_photos": "அறுவடை புகைப்படங்களைத் தேர்ந்தெடுக்கவும் அல்லது எடுக்கவும்",
            "add_more_photos": "கூடுதல் புகைப்படங்களைச் சேர்க்கவும் ({{remaining}} மீதமுள்ளது)",
            "confirm_delete_photo": "இந்தப் பட்டியலிலிருந்து இந்த புகைப்படத்தை நிச்சயமாக அகற்ற விரும்புகிறீர்களா?",
            "image_uploaded_success": "புகைப்படங்கள் வெற்றிகரமாகப் பதிவேற்றப்பட்டன.",
            "image_deleted_success": "படம் வெற்றிகரமாக நீக்கப்பட்டது.",
            "primary_thumbnail_updated": "முதன்மை பட்டியல் சிறுபடம் புதுப்பிக்கப்பட்டது.",
            "reorder_success": "படங்களின் காட்சி வரிசை புதுப்பிக்கப்பட்டது.",
            "manage_photos_title": "விளைபொருள் புகைப்படங்களை நிர்வகிக்கவும்",
            "photos_attached_count": "{{count}}/{{max}} படங்கள் இணைக்கப்பட்டுள்ளன",
            "attached_photos_heading": "இணைக்கப்பட்ட விளைபொருள் படங்கள் ({{count}}/{{max}})",
            "no_photos_yet": "இன்னும் படங்கள் எதுவும் இணைக்கப்படவில்லை",
            "upload_photos_hint": "வணிக வாங்குபவர்களை ஈர்க்க உங்கள் விளைபொருளின் தெளிவான புகைப்படங்களைப் பதிவேற்றவும்.",
            "primary_thumbnail": "முதன்மை சிறுபடம்",
            "make_primary": "முதன்மை ஆக்கு",
            "catalog_display_photo": "பட்டியல் காட்சிப் படம்",
            "move_earlier": "முன்னே நகர்த்து",
            "move_later": "பின்னே நகர்த்து",
            "delete_photo": "படத்தை நீக்கு",
            "upload_new_photo": "புதிய படம்(கள்) பதிவேற்றவும்",
            "set_as_primary": "முதன்மை படமாக அமை",
            "image_spec_hint": "மொத்தம் அதிகபட்சம் 10 படங்கள் • தலா 5 MB • JPEG, PNG அல்லது WebP",
            "upload_photo_btn": "படம்(கள்) பதிவேற்றவும்"
        },
        "errors": {
            "image_limit_reached": "ஒரு பட்டியலுக்கு அதிகபட்சம் 10 புகைப்படங்கள் என்ற வரம்பு எட்டப்பட்டது.",
            "image_size_exceeded": "படத்தின் அளவு 5 MB வரம்பைத் தாண்டியது.",
            "unsupported_image_format": "ஆதரிக்கப்படாத பட வடிவம். தயவுசெய்து JPEG, PNG அல்லது WebP படத்தைத் தேர்ந்தெடுக்கவும்.",
            "select_image_first": "பதிவேற்ற படக் கோப்பைத் தேர்ந்தெடுக்கவும்.",
            "upload_failed": "படத்தைப் பதிவேற்ற முடியவில்லை. மீண்டும் முயற்சிக்கவும்.",
            "network_error_upload": "படத்தைப் பதிவேற்றும் போது பிணையப் பிழை ஏற்பட்டது.",
            "delete_failed": "படத்தை நீக்க முடியவில்லை.",
            "primary_failed": "முதன்மைப் படத்தை நியமிக்க முடியவில்லை."
        },
        "marketplace": {
            "catalog_primary_photo": "பட்டியல் முதன்மைப் புகைப்படம்",
            "thumbnail_n": "சிறுபடம் {{n}}",
            "no_photos_uploaded": "இந்த விளைபொருளுக்கு புகைப்படங்கள் எதுவும் பதிவேற்றப்படவில்லை"
        }
    },
    "te": {
        "dashboard": {
            "produce_photos_title": "ఉత్పత్తి లాట్ ఛాయాచిత్రాలు",
            "photo_limits_guidance": "గరిష్టంగా 10 ఫోటోలు, ఒక్కొక్కటి 5 MB (JPEG, PNG, WebP)",
            "current_photos_label": "ప్రస్తుత ఛాయాచిత్రాలు:",
            "make_primary_photo": "ప్రధాన ఫోటోగా చేయండి",
            "primary_photo_badge": "ప్రధాన",
            "photos_to_upload_label": "అప్‌లోడ్ చేయవలసిన ఫోటోలు:",
            "set_primary": "ప్రధానంగా సెట్ చేయండి",
            "add_first_photos": "పంట ఫోటోలను ఎంచుకోండి లేదా తీయండి",
            "add_more_photos": "మరిన్ని ఫోటోలను జోడించండి ({{remaining}} మిగిలి ఉన్నాయి)",
            "confirm_delete_photo": "మీరు ఖచ్చితంగా ఈ జాబితా నుండి ఈ ఫోటోను తొలగించాలనుకుంటున్నారా?",
            "image_uploaded_success": "ఫోటోలు విజయవంతంగా అప్‌లోడ్ చేయబడ్డాయి.",
            "image_deleted_success": "చిత్రం విజయవంతంగా తొలగించబడింది.",
            "primary_thumbnail_updated": "ప్రధాన కేటలాగ్ థంబ్‌నెయిల్ నవీకరించబడింది.",
            "reorder_success": "చిత్ర ప్రదర్శన క్రమం నవీకరించబడింది.",
            "manage_photos_title": "ఉత్పత్తి ఫోటోలను నిర్వహించండి",
            "photos_attached_count": "{{count}}/{{max}} ఫోటోలు జోడించబడ్డాయి",
            "attached_photos_heading": "జోడించిన ఉత్పత్తి ఫోటోలు ({{count}}/{{max}})",
            "no_photos_yet": "ఇంకా ఫోటోలు ఏవీ జోడించబడలేదు",
            "upload_photos_hint": "వాణిజ్య కొనుగోలుదారులను ఆకర్షించడానికి మీ పంట ఉత్పత్తుల స్పష్టమైన ఫోటోలను అప్‌లోడ్ చేయండి.",
            "primary_thumbnail": "ప్రధాన థంబ్‌నెయిల్",
            "make_primary": "ప్రధానంగా చేయండి",
            "catalog_display_photo": "కేటలాగ్ ప్రదర్శన ఫోటో",
            "move_earlier": "ముందుకు జరపండి",
            "move_later": "వెనుకకు జరపండి",
            "delete_photo": "ఫోటోను తొలగించండి",
            "upload_new_photo": "కొత్త ఫోటో(లు) అప్‌లోడ్ చేయండి",
            "set_as_primary": "ప్రధాన ఫోటోగా సెట్ చేయండి",
            "image_spec_hint": "మొత్తం గరిష్టంగా 10 ఫోటోలు • ఒక్కొక్కటి 5 MB • JPEG, PNG లేదా WebP",
            "upload_photo_btn": "ఫోటో(లు) అప్‌లోడ్ చేయండి"
        },
        "errors": {
            "image_limit_reached": "జాబితాకు గరిష్ట పరిమితి 10 ఫోటోలు చేరింది.",
            "image_size_exceeded": "చిత్రం పరిమాణం 5 MB పరిమితిని మించిపోయింది.",
            "unsupported_image_format": "మద్దతు లేని చిత్రం ఫార్మాట్. దయచేసి JPEG, PNG లేదా WebP ఫోటోను ఎంచుకోండి.",
            "select_image_first": "దయచేసి అప్‌లోడ్ చేయడానికి చిత్రం ఫైల్‌ను ఎంచుకోండి.",
            "upload_failed": "చిత్రం అప్‌లోడ్ విఫలమైంది. దయచేసి మళ్లీ ప్రయత్నించండి.",
            "network_error_upload": "ఫోటోను అప్‌లోడ్ చేస్తున్నప్పుడు నెట్‌వర్క్ లోపం సంభవించింది.",
            "delete_failed": "చిత్రాన్ని తొలగించడంలో విఫలమైంది.",
            "primary_failed": "ప్రధాన చిత్రాన్ని నిర్దేశించడంలో విఫలమైంది."
        },
        "marketplace": {
            "catalog_primary_photo": "కేటలాగ్ ప్రధాన ఫోటో",
            "thumbnail_n": "థంబ్‌నెయిల్ {{n}}",
            "no_photos_uploaded": "ఈ ఉత్పత్తి లాట్ కోసం ఛాయాచిత్రాలు అప్‌లోడ్ చేయబడలేదు"
        }
    },
    "kn": {
        "dashboard": {
            "produce_photos_title": "ಉತ್ಪನ್ನ ಲಾಟ್ ಛಾಯಾಚಿತ್ರಗಳು",
            "photo_limits_guidance": "ಗರಿಷ್ಠ 10 ಫೋಟೋಗಳು, ತಲಾ 5 MB (JPEG, PNG, WebP)",
            "current_photos_label": "ಪ್ರಸ್ತುತ ಛಾಯಾಚಿತ್ರಗಳು:",
            "make_primary_photo": "ಮುಖ್ಯ ಫೋಟೋ ಮಾಡಿ",
            "primary_photo_badge": "ಮುಖ್ಯ",
            "photos_to_upload_label": "ಅಪ್‌ಲೋಡ್ ಮಾಡಬೇಕಾದ ಛಾಯಾಚಿತ್ರಗಳು:",
            "set_primary": "ಮುಖ್ಯವಾಗಿ ಹೊಂದಿಸಿ",
            "add_first_photos": "ಬೆಳೆ ಛಾಯಾಚಿತ್ರಗಳನ್ನು ಆಯ್ಕೆಮಾಡಿ ಅಥವಾ ಸೆರೆಹಿಡಿಯಿರಿ",
            "add_more_photos": "ಇನ್ನಷ್ಟು ಫೋಟೋಗಳನ್ನು ಸೇರಿಸಿ ({{remaining}} ಉಳಿದಿದೆ)",
            "confirm_delete_photo": "ಪಟ್ಟಿಯಿಂದ ಈ ಛಾಯಾಚಿತ್ರವನ್ನು ಖಚಿತವಾಗಿ ತೆಗೆದುಹಾಕಲು ನೀವು ಬಯಸುವಿರಾ?",
            "image_uploaded_success": "ಛಾಯಾಚಿತ್ರಗಳನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಅಪ್‌ಲೋಡ್ ಮಾಡಲಾಗಿದೆ.",
            "image_deleted_success": "ಚಿತ್ರವನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಅಳಿಸಲಾಗಿದೆ.",
            "primary_thumbnail_updated": "ಮುಖ್ಯ ಕ್ಯಾಟಲಾಗ್ ಥಂಬ್‌ನೇಲ್ ನವೀಕರಿಸಲಾಗಿದೆ.",
            "reorder_success": "ಚಿತ್ರ ಪ್ರದರ್ಶನ ಕ್ರಮವನ್ನು ನವೀಕರಿಸಲಾಗಿದೆ.",
            "manage_photos_title": "ಉತ್ಪನ್ನ ಫೋಟೋಗಳನ್ನು ನಿರ್ವಹಿಸಿ",
            "photos_attached_count": "{{count}}/{{max}} ಫೋಟೋಗಳನ್ನು ಲಗತ್ತಿಸಲಾಗಿದೆ",
            "attached_photos_heading": "ಲಗತ್ತಿಸಲಾದ ಉತ್ಪನ್ನ ಫೋಟೋಗಳು ({{count}}/{{max}})",
            "no_photos_yet": "ಇನ್ನೂ ಯಾವುದೇ ಫೋಟೋಗಳನ್ನು ಲಗತ್ತಿಸಲಾಗಿಲ್ಲ",
            "upload_photos_hint": "ವಾಣಿಜ್ಯ ಖರೀದಿದಾರರನ್ನು ಆಕರ್ಷಿಸಲು ನಿಮ್ಮ ಕಟಾವು ಉತ್ಪನ್ನದ ಸ್ಪಷ್ಟ ಫೋಟೋಗಳನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಿ.",
            "primary_thumbnail": "ಮುಖ್ಯ ಥಂಬ್‌ನೇಲ್",
            "make_primary": "ಮುಖ್ಯ ಚಿತ್ರವಾಗಿಸಿ",
            "catalog_display_photo": "ಕ್ಯಾಟಲಾಗ್ ಪ್ರದರ್ಶನ ಫೋಟೋ",
            "move_earlier": "ಹಿಂದಕ್ಕೆ ಸರಿಸಿ",
            "move_later": "ಮುಂದಕ್ಕೆ ಸರಿಸಿ",
            "delete_photo": "ಫೋಟೋ ಅಳಿಸಿ",
            "upload_new_photo": "ಹೊಸ ಫೋಟೋ(ಗಳನ್ನು) ಅಪ್‌ಲೋಡ್ ಮಾಡಿ",
            "set_as_primary": "ಮುಖ್ಯ ಚಿತ್ರವಾಗಿ ಹೊಂದಿಸಿ",
            "image_spec_hint": "ಒಟ್ಟು ಗರಿಷ್ಠ 10 ಫೋಟೋಗಳು • ತಲಾ 5 MB • JPEG, PNG ಅಥವಾ WebP",
            "upload_photo_btn": "ಫೋಟೋ(ಗಳನ್ನು) ಅಪ್‌ಲೋಡ್ ಮಾಡಿ"
        },
        "errors": {
            "image_limit_reached": "ಪ್ರತಿ ಪಟ್ಟಿಗೆ ಗರಿಷ್ಠ 10 ಫೋಟೋಗಳ ಮಿತಿ ತಲುಪಿದೆ.",
            "image_size_exceeded": "ಚಿತ್ರದ ಗಾತ್ರವು 5 MB ಮಿತಿಯನ್ನು ಮೀರಿದೆ.",
            "unsupported_image_format": "ಬೆಂಬಲವಿಲ್ಲದ ಚಿತ್ರ ಸ್ವರೂಪ. ದಯವಿಟ್ಟು JPEG, PNG ಅಥವಾ WebP ಫೋಟೋ ಆಯ್ಕೆಮಾಡಿ.",
            "select_image_first": "ಅಪ್‌ಲೋಡ್ ಮಾಡಲು ದಯವಿಟ್ಟು ಚಿತ್ರ ಫೈಲ್ ಆಯ್ಕೆಮಾಡಿ.",
            "upload_failed": "ಚಿತ್ರ ಅಪ್‌ಲೋಡ್ ವಿಫಲವಾಗಿದೆ. ದಯವಿಟ್ಟು ಪುನಃ ಪ್ರಯತ್ನಿಸಿ.",
            "network_error_upload": "ಫೋಟೋ ಅಪ್‌ಲೋಡ್ ಮಾಡುವಾಗ ನೆಟ್‌ವರ್ಕ್ ದೋಷ ಸಂಭವಿಸಿದೆ.",
            "delete_failed": "ಚಿತ್ರವನ್ನು ಅಳಿಸಲು ವಿಫಲವಾಗಿದೆ.",
            "primary_failed": "ಮುಖ್ಯ ಚಿತ್ರವನ್ನು ಗೊತ್ತುಪಡಿಸಲು ವಿಫಲವಾಗಿದೆ."
        },
        "marketplace": {
            "catalog_primary_photo": "ಕ್ಯಾಟಲಾಗ್ ಮುಖ್ಯ ಫೋಟೋ",
            "thumbnail_n": "ಥಂಬ್‌ನೇಲ್ {{n}}" ,
            "no_photos_uploaded": "ಈ ಉತ್ಪನ್ನದ ಲಾಟ್‌ಗಾಗಿ ಯಾವುದೇ ಛಾಯಾಚಿತ್ರಗಳನ್ನು ಅಪ್‌ಲೋಡ್ ಮಾಡಲಾಗಿಲ್ಲ"
        }
    },
    "ml": {
        "dashboard": {
            "produce_photos_title": "വിളവ് ലോട്ടുകളുടെ ഫോട്ടോകൾ",
            "photo_limits_guidance": "പരമാവധി 10 ഫോട്ടോകൾ, ഓരോന്നിനും 5 MB (JPEG, PNG, WebP)",
            "current_photos_label": "നിലവിലുള്ള ഫോട്ടോകൾ:",
            "make_primary_photo": "പ്രധാന ഫോട്ടോയാക്കുക",
            "primary_photo_badge": "പ്രധാനം",
            "photos_to_upload_label": "അപ്‌ലോഡ് ചെയ്യേണ്ട ഫോട്ടോകൾ:",
            "set_primary": "പ്രധാനമായി സജ്ജമാക്കുക",
            "add_first_photos": "വിളവെടുപ്പ് ഫോട്ടോകൾ തിരഞ്ഞെടുക്കുക അല്ലെങ്കിൽ എടുക്കുക",
            "add_more_photos": "കൂടുതൽ ഫോട്ടോകൾ ചേർക്കുക ({{remaining}} എണ്ണം ബാക്കി)",
            "confirm_delete_photo": "ഈ ലിസ്റ്റിംഗിൽ നിന്ന് ഈ ഫോട്ടോ നീക്കംചെയ്യാൻ നിങ്ങൾ ആഗ്രഹിക്കുന്നുണ്ടോ?",
            "image_uploaded_success": "ഫോട്ടോകൾ വിജയകരമായി അപ്‌ലോഡ് ചെയ്തു.",
            "image_deleted_success": "ചിത്രം വിജയകരമായി നീക്കംചെയ്തു.",
            "primary_thumbnail_updated": "പ്രധാന കാറ്റലോഗ് ലഘുചിത്രം അപ്‌ഡേറ്റുചെയ്‌തു.",
            "reorder_success": "ചിത്ര പ്രദർശന ക്രമം അപ്‌ഡേറ്റുചെയ്‌തു.",
            "manage_photos_title": "വിളവ് ഫോട്ടോകൾ കൈകാര്യം ചെയ്യുക",
            "photos_attached_count": "{{count}}/{{max}} ഫോട്ടോകൾ ചേർത്തു",
            "attached_photos_heading": "ചേർത്ത വിളവ് ഫോട്ടോകൾ ({{count}}/{{max}})",
            "no_photos_yet": "ഇതുവരെ ഫോട്ടോകൾ ചേർത്തിട്ടില്ല",
            "upload_photos_hint": "വാണിജ്യ വാങ്ങലുകാരെ ആകർഷിക്കാൻ നിങ്ങളുടെ വിളവെടുപ്പ് ലോട്ടിന്റെ വ്യക്തമായ ഫോട്ടോകൾ അപ്‌ലോഡ് ചെയ്യുക.",
            "primary_thumbnail": "പ്രധാന ലഘുചിത്രം",
            "make_primary": "പ്രധാന ഫോട്ടോയാക്കുക",
            "catalog_display_photo": "കാറ്റലോഗ് പ്രദർശന ഫോട്ടോ",
            "move_earlier": "മുന്നോട്ട് മാറ്റുക",
            "move_later": "പിന്നോട്ട് മാറ്റുക",
            "delete_photo": "ഫോട്ടോ ഇല്ലാതാക്കുക",
            "upload_new_photo": "പുതിയ ഫോട്ടോകൾ അപ്‌ലോഡ് ചെയ്യുക",
            "set_as_primary": "പ്രധാന ഫോട്ടോയായി സജ്ജമാക്കുക",
            "image_spec_hint": "ആകെ പരമാവധി 10 ഫോട്ടോകൾ • ഓരോന്നിനും 5 MB • JPEG, PNG അല്ലെങ്കിൽ WebP",
            "upload_photo_btn": "ഫോട്ടോ(കൾ) അപ്‌ലോഡ് ചെയ്യുക"
        },
        "errors": {
            "image_limit_reached": "ഒരു ലിസ്റ്റിംഗിൽ പരമാവധി 10 ഫോട്ടോകൾ എന്ന പരിധി എത്തിക്കഴിഞ്ഞു.",
            "image_size_exceeded": "ചിത്രത്തിന്റെ വലിപ്പം 5 MB പരിധി കവിയുന്നു.",
            "unsupported_image_format": "പിന്തുണയ്‌ക്കാത്ത ഇമേജ് ഫോർമാറ്റ്. JPEG, PNG അല്ലെങ്കിൽ WebP ഫോട്ടോ തിരഞ്ഞെടുക്കുക.",
            "select_image_first": "അപ്‌ലോഡ് ചെയ്യാൻ ഒരു ഇമേജ് ഫയൽ തിരഞ്ഞെടുക്കുക.",
            "upload_failed": "ചിത്രം അപ്‌ലോഡ് ചെയ്യുന്നതിൽ പരാജയപ്പെട്ടു. ദയവായി വീണ്ടും ശ്രമിക്കുക.",
            "network_error_upload": "ഫോട്ടോ അപ്‌ലോഡ് ചെയ്യുമ്പോൾ നെറ്റ്‌വർക്ക് തകരാറുണ്ടായി.",
            "delete_failed": "ചിത്രം ഇല്ലാതാക്കുന്നതിൽ പരാജയപ്പെട്ടു.",
            "primary_failed": "പ്രധാന ചിത്രം നിശ്ചയിക്കുന്നതിൽ പരാജയപ്പെട്ടു."
        },
        "marketplace": {
            "catalog_primary_photo": "കാറ്റലോഗ് പ്രധാന ഫോട്ടോ",
            "thumbnail_n": "ലഘുചിത്രം {{n}}",
            "no_photos_uploaded": "ഈ വിളവ് ലോട്ടിനായി ഫോട്ടോകളൊന്നും അപ്‌ലോഡ് ചെയ്തിട്ടില്ല"
        }
    },
    "pa": {
        "dashboard": {
            "produce_photos_title": "ਉਪਜ ਲਾਟ ਦੀਆਂ ਤਸਵੀਰਾਂ",
            "photo_limits_guidance": "ਵੱਧ ਤੋਂ ਵੱਧ 10 ਫੋਟੋਆਂ, ਹਰੇਕ 5 MB (JPEG, PNG, WebP)",
            "current_photos_label": "ਮੌਜੂਦਾ ਤਸਵੀਰਾਂ:",
            "make_primary_photo": "ਮੁੱਖ ਫੋਟੋ ਬਣਾਓ",
            "primary_photo_badge": "ਮੁੱਖ",
            "photos_to_upload_label": "ਅਪਲੋਡ ਕਰਨ ਵਾਲੀਆਂ ਤਸਵੀਰਾਂ:",
            "set_primary": "ਮੁੱਖ ਸੈੱਟ ਕਰੋ",
            "add_first_photos": "ਫਸਲ ਦੀਆਂ ਫੋਟੋਆਂ ਚੁਣੋ ਜਾਂ ਖਿੱਚੋ",
            "add_more_photos": "ਹੋਰ ਫੋਟੋਆਂ ਸ਼ਾਮਲ ਕਰੋ ({{remaining}} ਬਾਕੀ)",
            "confirm_delete_photo": "ਕੀ ਤੁਸੀਂ ਯਕੀਨੀ ਤੌਰ 'ਤੇ ਇਸ ਸੂਚੀ ਵਿੱਚੋਂ ਇਹ ਫੋਟੋ ਹਟਾਉਣਾ ਚਾਹੁੰਦੇ ਹੋ?",
            "image_uploaded_success": "ਤਸਵੀਰਾਂ ਸਫਲਤਾਪੂਰਵਕ ਅਪਲੋਡ ਹੋ ਗਈਆਂ।",
            "image_deleted_success": "ਤਸਵੀਰ ਸਫਲਤਾਪੂਰਵਕ ਹਟਾਈ ਗਈ।",
            "primary_thumbnail_updated": "ਮੁੱਖ ਕੈਟਾਲਾਗ ਥੰਬਨੇਲ ਅੱਪਡੇਟ ਕੀਤਾ ਗਿਆ।",
            "reorder_success": "ਤਸਵੀਰ ਪ੍ਰਦਰਸ਼ਨ ਕ੍ਰਮ ਅੱਪਡੇਟ ਕੀਤਾ ਗਿਆ।",
            "manage_photos_title": "ਉਪਜ ਦੀਆਂ ਫੋਟੋਆਂ ਦਾ ਪ੍ਰਬੰਧਨ ਕਰੋ",
            "photos_attached_count": "{{count}}/{{max}} ਫੋਟੋਆਂ ਸ਼ਾਮਲ ਹਨ",
            "attached_photos_heading": "ਸ਼ਾਮਲ ਉਪਜ ਫੋਟੋਆਂ ({{count}}/{{max}})",
            "no_photos_yet": "ਅਜੇ ਕੋਈ ਫੋਟੋ ਸ਼ਾਮਲ ਨਹੀਂ ਕੀਤੀ ਗਈ",
            "upload_photos_hint": "ਵਪਾਰਕ ਖਰੀਦਦਾਰਾਂ ਨੂੰ ਆਕਰਸ਼ਿਤ ਕਰਨ ਲਈ ਆਪਣੀ ਉਪਜ ਦੀਆਂ ਸਾਫ਼ ਫੋਟੋਆਂ ਅਪਲੋਡ ਕਰੋ।",
            "primary_thumbnail": "ਮੁੱਖ ਥੰਬਨੇਲ",
            "make_primary": "ਮੁੱਖ ਬਣਾਓ",
            "catalog_display_photo": "ਕੈਟਾਲਾਗ ਡਿਸਪਲੇ ਫੋਟੋ",
            "move_earlier": "ਪਹਿਲਾਂ ਕਰੋ",
            "move_later": "ਬਾਅਦ ਵਿੱਚ ਕਰੋ",
            "delete_photo": "ਫੋਟੋ ਹਟਾਓ",
            "upload_new_photo": "ਨਵੀਂ ਫੋਟੋ ਅਪਲੋਡ ਕਰੋ",
            "set_as_primary": "ਮੁੱਖ ਵਜੋਂ ਸੈੱਟ ਕਰੋ",
            "image_spec_hint": "ਕੁੱਲ ਵੱਧ ਤੋਂ ਵੱਧ 10 ਫੋਟੋਆਂ • ਹਰੇਕ 5 MB • JPEG, PNG ਜਾਂ WebP",
            "upload_photo_btn": "ਫੋਟੋ ਅਪਲੋਡ ਕਰੋ"
        },
        "errors": {
            "image_limit_reached": "ਪ੍ਰਤੀ ਸੂਚੀ ਵੱਧ ਤੋਂ ਵੱਧ 10 ਫੋਟੋਆਂ ਦੀ ਸੀਮਾ ਪੂਰੀ ਹੋ ਗਈ ਹੈ।",
            "image_size_exceeded": "ਫੋਟੋ ਦਾ ਆਕਾਰ 5 MB ਸੀਮਾ ਤੋਂ ਵੱਧ ਹੈ।",
            "unsupported_image_format": "ਅਸਮਰਥਿਤ ਚਿੱਤਰ ਫਾਰਮੈਟ। ਕਿਰਪਾ ਕਰਕੇ JPEG, PNG ਜਾਂ WebP ਫੋਟੋ ਚੁਣੋ।",
            "select_image_first": "ਕਿਰਪਾ ਕਰਕੇ ਅਪਲੋਡ ਕਰਨ ਲਈ ਇੱਕ ਫੋਟੋ ਫਾਈਲ ਚੁਣੋ।",
            "upload_failed": "ਫੋਟੋ ਅਪਲੋਡ ਅਸਫਲ ਰਹੀ। ਕਿਰਪਾ ਕਰਕੇ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
            "network_error_upload": "ਫੋਟੋ ਅਪਲੋਡ ਕਰਦੇ ਸਮੇਂ ਇੱਕ ਨੈੱਟਵਰਕ ਗਲਤੀ ਆਈ।",
            "delete_failed": "ਫੋਟੋ ਹਟਾਉਣ ਵਿੱਚ ਅਸਫਲ।",
            "primary_failed": "ਮੁੱਖ ਫੋਟੋ ਨਿਰਧਾਰਤ ਕਰਨ ਵਿੱਚ ਅਸਫਲ।"
        },
        "marketplace": {
            "catalog_primary_photo": "ਕੈਟਾਲਾਗ ਮੁੱਖ ਫੋਟੋ",
            "thumbnail_n": "ਥੰਬਨੇਲ {{n}}",
            "no_photos_uploaded": "ਇਸ ਉਪਜ ਲਾਟ ਲਈ ਕੋਈ ਤਸਵੀਰ ਅਪਲੋਡ ਨਹੀਂ ਕੀਤੀ ਗਈ ਹੈ"
        }
    },
    "or": {
        "dashboard": {
            "produce_photos_title": "ଉତ୍ପାଦନ ଲଟ୍ ଫଟୋଗ୍ରାଫ୍",
            "photo_limits_guidance": "ସର୍ବାଧିକ ୧୦ ଫଟୋ, ପ୍ରତ୍ୟେକ ୫ MB (JPEG, PNG, WebP)",
            "current_photos_label": "ବିଦ୍ୟମାନ ଫଟୋ:",
            "make_primary_photo": "ପ୍ରାଥମିକ ଫଟୋ କରନ୍ତୁ",
            "primary_photo_badge": "ପ୍ରାଥମିକ",
            "photos_to_upload_label": "ଅପଲୋଡ୍ ହେବାକୁ ଥିବା ଫଟୋ:",
            "set_primary": "ପ୍ରାଥମିକ ସେଟ୍ କରନ୍ତୁ",
            "add_first_photos": "ଅମଳ ଫଟୋ ଚୟନ କରନ୍ତୁ କିମ୍ବା ଉଠାନ୍ତୁ",
            "add_more_photos": "ଅଧିକ ଫଟୋ ଯୋଡ଼ନ୍ତୁ ({{remaining}} ବାକି)",
            "confirm_delete_photo": "ଆପଣ ନିଶ୍ଚିତ କି ଏହି ତାଲିକାରୁ ଏହି ଫଟୋ ହଟାଇବାକୁ ଚାହୁଁଛନ୍ତି?",
            "image_uploaded_success": "ଫଟୋ ସଫଳତାର ସହ ଅପଲୋଡ୍ ହେଲା।",
            "image_deleted_success": "ଫଟୋ ସଫଳତାର ସହ ହଟାଗଲା।",
            "primary_thumbnail_updated": "ପ୍ରାଥମିକ କାଟାଲଗ୍ ଥମ୍ବନେଲ୍ ଅପଡେଟ୍ ହେଲା।",
            "reorder_success": "ଛବି ପ୍ରଦର୍ଶନ କ୍ରମ ଅପଡେଟ୍ ହେଲା।",
            "manage_photos_title": "ଉତ୍ପାଦନ ଫଟୋ ପରିଚାଳନା କରନ୍ତୁ",
            "photos_attached_count": "{{count}}/{{max}} ଫଟୋ ସଂଲଗ୍ନ ହୋଇଛି",
            "attached_photos_heading": "ସଂଲଗ୍ନ ଉତ୍ପାଦନ ଫଟୋ ({{count}}/{{max}})",
            "no_photos_yet": "ଏପର୍ଯ୍ୟନ୍ତ କୌଣସି ଫଟୋ ସଂଲଗ୍ନ ହୋଇନାହିଁ",
            "upload_photos_hint": "ବାଣିଜ୍ୟିକ କ୍ରେତାମାନଙ୍କୁ ଆକର୍ଷିତ କରିବା ପାଇଁ ଆପଣଙ୍କ ଫସଲର ସ୍ପଷ୍ଟ ଫଟୋ ଅପଲୋଡ୍ କରନ୍ତୁ।",
            "primary_thumbnail": "ପ୍ରାଥମିକ ଥମ୍ବନେଲ୍",
            "make_primary": "ପ୍ରାଥମିକ କରନ୍ତୁ",
            "catalog_display_photo": "କାଟାଲଗ୍ ପ୍ରଦର୍ଶନ ଫଟୋ",
            "move_earlier": "ଆଗକୁ ନିଅନ୍ତୁ",
            "move_later": "ପଛକୁ ନିଅନ୍ତୁ",
            "delete_photo": "ଫଟୋ ହଟାନ୍ତୁ",
            "upload_new_photo": "ନୂତନ ଫଟୋ ଅପଲୋଡ୍ କରନ୍ତୁ",
            "set_as_primary": "ପ୍ରାଥମିକ ଭାବରେ ସେଟ୍ କରନ୍ତୁ",
            "image_spec_hint": "ସର୍ବମୋଟ ୧୦ ଫଟୋ • ପ୍ରତ୍ୟେକ ୫ MB • JPEG, PNG କିମ୍ବା WebP",
            "upload_photo_btn": "ଫଟୋ ଅପଲୋଡ୍ କରନ୍ତୁ"
        },
        "errors": {
            "image_limit_reached": "ପ୍ରତି ତାଲିକାରେ ସର୍ବାଧିକ ୧୦ ଫଟୋର ସୀମା ପହଞ୍ଚିଛି।",
            "image_size_exceeded": "ଛବିର ଆକାର ୫ MB ସୀମା ଅତିକ୍ରମ କରିଛି।",
            "unsupported_image_format": "ଅସମର୍ଥିତ ଛବି ଫର୍ମାଟ୍। ଦୟାକରି JPEG, PNG କିମ୍ବା WebP ଫଟୋ ବାଛନ୍ତୁ।",
            "select_image_first": "ଦୟାକରି ଅପଲୋଡ୍ କରିବା ପାଇଁ ଏକ ଛବି ଫାଇଲ୍ ଚୟନ କରନ୍ତୁ।",
            "upload_failed": "ଛବି ଅପଲୋଡ୍ ବିଫଳ ହେଲା। ଦୟାକରି ପୁନଃ ଚେଷ୍ଟା କରନ୍ତୁ।",
            "network_error_upload": "ଫଟୋ ଅପଲୋଡ୍ କରିବା ସମୟରେ ଏକ ନେଟୱାର୍କ ତ୍ରୁଟି ଘଟିଲା।",
            "delete_failed": "ଛବି ହଟାଇବାରେ ବିଫଳ।",
            "primary_failed": "ପ୍ରାଥମିକ ଛବି ନିର୍ଦ୍ଧାରଣ କରିବାରେ ବିଫଳ।"
        },
        "marketplace": {
            "catalog_primary_photo": "କାଟାଲଗ୍ ପ୍ରାଥମିକ ଫଟୋ",
            "thumbnail_n": "ଥମ୍ବନେଲ୍ {{n}}",
            "no_photos_uploaded": "ଏହି ଉତ୍ପାଦନ ଲଟ୍ ପାଇଁ କୌଣସି ଫଟୋ ଅପଲୋଡ୍ ହୋଇନାହିଁ"
        }
    },
    "as": {
        "dashboard": {
            "produce_photos_title": "শস্য লটৰ আলোকচিত্ৰ",
            "photo_limits_guidance": "সৰ্বাধিক ১০ খন ফটো, প্ৰতিখন ৫ MB (JPEG, PNG, WebP)",
            "current_photos_label": "বৰ্তমানৰ আলোকচিত্ৰ:",
            "make_primary_photo": "প্ৰাথমিক ফটো কৰক",
            "primary_photo_badge": "প্ৰাথমিক",
            "photos_to_upload_label": "আপলোড কৰিবলগীয়া আলোকচিত্ৰ:",
            "set_primary": "প্ৰাথমিক হিচাপে ছেট কৰক",
            "add_first_photos": "শস্যৰ ফটো বাছনি কৰক বা তোলক",
            "add_more_photos": "অধিক ফটো যোগ কৰক ({{remaining}} বাকী)",
            "confirm_delete_photo": "আপুনি নিশ্চিতনে এই তালিকাৰ পৰা এই ফটোখন আঁতৰাব বিচাৰে?",
            "image_uploaded_success": "আলোকচিত্ৰ সফলতাৰে আপলোড হ'ল।",
            "image_deleted_success": "ছবি সফলতাৰে মচি পেলোৱা হ'ল।",
            "primary_thumbnail_updated": "প্ৰাথমিক তালিকা থাম্বনেইল আপডেট কৰা হ'ল।",
            "reorder_success": "ছবি প্ৰদৰ্শনৰ ক্ৰম আপডেট কৰা হ'ল।",
            "manage_photos_title": "শস্যৰ ফটো পৰিচালনা কৰক",
            "photos_attached_count": "{{count}}/{{max}} ফটো সংলগ্ন কৰা হৈছে",
            "attached_photos_heading": "সংলগ্ন শস্যৰ ফটো ({{count}}/{{max}})",
            "no_photos_yet": "এতিয়ালৈকে কোনো ফটো সংলগ্ন কৰা হোৱা নাই",
            "upload_photos_hint": "ব্যৱসায়িক ক্ৰেতাক আকৰ্ষিত কৰিবলৈ আপোনাৰ শস্যৰ স্পষ্ট ফটো আপলোড কৰক।",
            "primary_thumbnail": "প্ৰাথমিক থাম্বনেইল",
            "make_primary": "প্ৰাথমিক কৰক",
            "catalog_display_photo": "তালিকা প্ৰদৰ্শন ফটো",
            "move_earlier": "আগবঢ়াওক",
            "move_later": "পিছুৱাওক",
            "delete_photo": "ফটো মচক",
            "upload_new_photo": "নতুন ফটো আপলোড কৰক",
            "set_as_primary": "প্ৰাথমিক হিচাপে নিৰ্ধাৰণ কৰক",
            "image_spec_hint": "মুঠ সৰ্বাধিক ১০ খন ফটো • প্ৰতিখন ৫ MB • JPEG, PNG বা WebP",
            "upload_photo_btn": "ফটো আপলোড কৰক"
        },
        "errors": {
            "image_limit_reached": "প্ৰতি তালিকাত সৰ্বাধিক ১০ খন ফটোৰ সীমা উকলি গৈছে।",
            "image_size_exceeded": "ছবিৰ আকাৰ ৫ MB সীমা অতিক্ৰম কৰিছে।",
            "unsupported_image_format": "অসমৰ্থিত ছবি বিন্যাস। অনুগ্ৰহ কৰি JPEG, PNG বা WebP ফটো বাছক।",
            "select_image_first": "অনুগ্ৰহ কৰি আপলোড কৰিবলৈ এখন ছবি বাছক।",
            "upload_failed": "ছবি আপলোড ব্যৰ্থ হ'ল। অনুগ্ৰহ কৰি পুনৰ চেষ্টা কৰক।",
            "network_error_upload": "ফটো আপলোড কৰাৰ সময়ত এটা নেটৱৰ্ক ত্ৰুটি ঘটিল।",
            "delete_failed": "ছবি মচি পেলাবলৈ ব্যৰ্থ।",
            "primary_failed": "প্ৰাথমিক ছবি নিৰ্ধাৰণ কৰাত ব্যৰ্থ।"
        },
        "marketplace": {
            "catalog_primary_photo": "তালিকাৰ প্ৰাথমিক ফটো",
            "thumbnail_n": "থাম্বনেইল {{n}}",
            "no_photos_uploaded": "এই শস্য লটৰ বাবে কোনো ফটো আপলোড কৰা হোৱা নাই"
        }
    },
    "ur": {
        "dashboard": {
            "produce_photos_title": "فصل لاٹ کی تصاویر",
            "photo_limits_guidance": "زیادہ سے زیادہ 10 تصاویر، فی تصویر 5 MB (JPEG, PNG, WebP)",
            "current_photos_label": "موجودہ تصاویر:",
            "make_primary_photo": "بنیادی تصویر بنائیں",
            "primary_photo_badge": "بنیادی",
            "photos_to_upload_label": "اپ لوڈ کے لیے تصاویر:",
            "set_primary": "بنیادی مقرر کریں",
            "add_first_photos": "فصل کی تصاویر منتخب کریں یا کھینچیں",
            "add_more_photos": "مزید تصاویر شامل کریں ({{remaining}} باقی)",
            "confirm_delete_photo": "کیا آپ واقعی اس فہرست سے یہ تصویر ہٹانا چاہتے ہیں؟",
            "image_uploaded_success": "تصاویر کامیابی کے ساتھ اپ لوڈ ہو گئیں۔",
            "image_deleted_success": "تصویر کامیابی سے حذف کر دی گئی۔",
            "primary_thumbnail_updated": "بنیادی کیٹلاگ تھمب نیل اپ ڈیٹ ہو گیا۔",
            "reorder_success": "تصاویر کی نمائش کی ترتیب اپ ڈیٹ کر دی گئی۔",
            "manage_photos_title": "فصل کی تصاویر کا انتظام",
            "photos_attached_count": "{{count}}/{{max}} تصاویر منسلک ہیں",
            "attached_photos_heading": "منسلک فصل کی تصاویر ({{count}}/{{max}})",
            "no_photos_yet": "ابھی تک کوئی تصویر منسلک نہیں ہے",
            "upload_photos_hint": "تجارتی خریداروں کو متوجہ کرنے کے لیے اپنی فصل کی صاف اور واضح تصاویر اپ لوڈ کریں۔",
            "primary_thumbnail": "بنیادی تھمب نیل",
            "make_primary": "بنیادی بنائیں",
            "catalog_display_photo": "کیٹلاگ ڈسپلے تصویر",
            "move_earlier": "پہلے لائیں",
            "move_later": "بعد میں لے جائیں",
            "delete_photo": "تصویر حذف کریں",
            "upload_new_photo": "نئی تصویر اپ لوڈ کریں",
            "set_as_primary": "بنیادی تصویر کے طور پر سیٹ کریں",
            "image_spec_hint": "کل زیادہ سے زیادہ 10 تصاویر • فی تصویر 5 MB • JPEG, PNG یا WebP",
            "upload_photo_btn": "تصویر اپ لوڈ کریں"
        },
        "errors": {
            "image_limit_reached": "فی فہرست زیادہ سے زیادہ 10 تصاویر کی حد پوری ہو چکی ہے۔",
            "image_size_exceeded": "تصویر کا سائز 5 MB کی حد سے زیادہ ہے۔",
            "unsupported_image_format": "غیر معاون تصویری فارمیٹ۔ برائے مہربانی JPEG, PNG یا WebP تصویر منتخب کریں۔",
            "select_image_first": "براہ کرم اپ لوڈ کرنے کے لیے تصویر منتخب کریں۔",
            "upload_failed": "تصویر اپ لوڈ کرنے میں ناکامی۔ براہ کرم دوبارہ کوشش کریں۔",
            "network_error_upload": "تصویر اپ لوڈ کرتے وقت نیٹ ورک خرابی پیش آئی۔",
            "delete_failed": "تصویر حذف کرنے میں ناکامی۔",
            "primary_failed": "بنیادی تصویر متعین کرنے میں ناکامی۔"
        },
        "marketplace": {
            "catalog_primary_photo": "کیٹلاگ بنیادی تصویر",
            "thumbnail_n": "تھمب نیل {{n}}",
            "no_photos_uploaded": "اس فصل لاٹ کے لیے کوئی تصویر اپ لوڈ نہیں کی گئی ہے"
        }
    },
    "ks": {
        "dashboard": {
            "produce_photos_title": "فصل لاٹ کی تصاویر",
            "photo_limits_guidance": "زیادہ کھوت زیادہ 10 فوٹو، پرٛتھ 5 MB (JPEG, PNG, WebP)",
            "current_photos_label": "موجودٕ تصاویر:",
            "make_primary_photo": "اہم تصویر بنائیو",
            "primary_photo_badge": "اہم",
            "photos_to_upload_label": "اپ لوڈ کرن والی تصویرٕ:",
            "set_primary": "اہم مقرر کٔریو",
            "add_first_photos": "فصل فوٹو ژاریو یا تلیو",
            "add_more_photos": "مزید فوٹو جوੜیو ({{remaining}} باقی)",
            "confirm_delete_photo": "کیا توہیہ چھی یژھان یہ تصویر لسٹ منزٕ کڑُن؟",
            "image_uploaded_success": "تصویرٕ گیہ کامیابی سان اپ لوڈ۔",
            "image_deleted_success": "تصویر گیہ کامیابی سان حذف۔",
            "primary_thumbnail_updated": "بنیادی کیٹلاگ تھمب نیل سپد اپ ڈیٹ۔",
            "reorder_success": "تصویر ہاونچ ترتیب سپز اپ ڈیٹ۔",
            "manage_photos_title": "فصل تصویرن ہند انتظام کٔریو",
            "photos_attached_count": "{{count}}/{{max}} فوٹو چھی رلِتھ",
            "attached_photos_heading": "رلِتھ فصل تصاویر ({{count}}/{{max}})",
            "no_photos_yet": "کانہہ تصویر چھی نہہ رلِتھ",
            "upload_photos_hint": "تجارتی خریدارن متوجہ کرنہ باپتھ اپ لوڈ کٔریو صاف تصویرٕ۔",
            "primary_thumbnail": "بنیادی تھمب نیل",
            "make_primary": "اہم بنائیو",
            "catalog_display_photo": "کیٹلاگ ڈسپلے فوٹو",
            "move_earlier": "برونٹھ کٔریو",
            "move_later": "پتھ کٔریو",
            "delete_photo": "تصویر ہٹائیو",
            "upload_new_photo": "نو فوٹو اپ لوڈ کٔریو",
            "set_as_primary": "اہم مقرر کٔریو",
            "image_spec_hint": "کل زیادہ کھوت زیادہ 10 فوٹو • پرٛتھ 5 MB • JPEG, PNG یا WebP",
            "upload_photo_btn": "فوٹو اپ لوڈ کٔریو"
        },
        "errors": {
            "image_limit_reached": "پرٛتھ لسٹنگ منز زیادہ کھوت زیادہ 10 فوٹو ہنز حد مکلییہ۔",
            "image_size_exceeded": "تصویر سائز چُھ 5 MB حد کھوت زیادتھ۔",
            "unsupported_image_format": "غیر معاون فارمیٹ۔ مہربانی کٔرتھ ژاریو JPEG, PNG یا WebP تصویر۔",
            "select_image_first": "مہربانی کٔرتھ ژاریو اپ لوڈ باپتھ فوٹو۔",
            "upload_failed": "فوٹو اپ لوڈ گژھنس منز ناکامی۔ دوبارہ کوشش کٔریو۔",
            "network_error_upload": "تصویر اپ لوڈ کرنس منز آئی نیٹ ورک خرابی۔",
            "delete_failed": "تصویر حذف کرنس منز ناکامی۔",
            "primary_failed": "بنیادی تصویر نامزد کرنس منز ناکامی۔"
        },
        "marketplace": {
            "catalog_primary_photo": "کیٹلاگ اہم فوٹو",
            "thumbnail_n": "تھمب نیل {{n}}",
            "no_photos_uploaded": "امِہ فصل لاٹ باپتھ چھی نہہ کانہہ تصویر اپ لوڈ کٔرمژ"
        }
    },
    "sd": {
        "dashboard": {
            "produce_photos_title": "فصل لاٽ جون تصويرون",
            "photo_limits_guidance": "وڌ ۾ وڌ 10 تصويرون، هر هڪ 5 MB (JPEG, PNG, WebP)",
            "current_photos_label": "موجود تصويرون:",
            "make_primary_photo": "بنيادي تصوير ٺاهيو",
            "primary_photo_badge": "بنيادي",
            "photos_to_upload_label": "اپ لوڊ ٿيڻ واريون تصويرون:",
            "set_primary": "بنيادي سيٽ ڪريو",
            "add_first_photos": "فصل جون تصويرون چونڊيو يا ڪڍو",
            "add_more_photos": "وڌيڪ تصويرون شامل ڪريو ({{remaining}} باقي)",
            "confirm_delete_photo": "ڇا توهان واقعي هن لسٽ مان هي تصوير هٽائڻ چاهيو ٿا؟",
            "image_uploaded_success": "تصويرون ڪاميابي سان اپ لوڊ ٿي ويون.",
            "image_deleted_success": "تصوير ڪاميابي سان ختم ڪئي وئي.",
            "primary_thumbnail_updated": "بنيادي ڪيٽلاگ ٿمب نيل اپڊيٽ ڪيو ويو.",
            "reorder_success": "تصويرن جي ڏيکاءُ وارو سلسلو اپڊيٽ ڪيو ويو.",
            "manage_photos_title": "فصل جي تصويرن جو انتظام",
            "photos_attached_count": "{{count}}/{{max}} تصويرون شامل آهن",
            "attached_photos_heading": "شامل فصل جون تصويرون ({{count}}/{{max}})",
            "no_photos_yet": "اڃا تائين ڪا تصوير شامل ناهي ڪئي وئي",
            "upload_photos_hint": "تجارتي خريدارن کي متوجه ڪرڻ لاءِ پنهنجي فصل جون صاف تصويرون اپ لوڊ ڪريو.",
            "primary_thumbnail": "بنيادي ٿمب نيل",
            "make_primary": "بنيادي ٺاهيو",
            "catalog_display_photo": "ڪيٽلاگ ڊسپلي تصوير",
            "move_earlier": "اڳتي ڪريو",
            "move_later": "پوئتي ڪريو",
            "delete_photo": "تصوير ختم ڪريو",
            "upload_new_photo": "نئين تصوير اپ لوڊ ڪريو",
            "set_as_primary": "بنيادي تصوير طور سيٽ ڪريو",
            "image_spec_hint": "ڪل وڌ ۾ وڌ 10 تصويرون • هر هڪ 5 MB • JPEG, PNG يا WebP",
            "upload_photo_btn": "تصوير اپ لوڊ ڪريو"
        },
        "errors": {
            "image_limit_reached": "في لسٽنگ وڌ ۾ وڌ 10 تصويرن جي حد پੂري ٿي چڪي آهي.",
            "image_size_exceeded": "تصوير جي سائيز 5 MB حد کان وڌيڪ آهي.",
            "unsupported_image_format": "غير معاون تصوير فارميٽ. مهرباني ڪري JPEG, PNG يا WebP تصوير چونڊيو.",
            "select_image_first": "مهرباني ڪري اپ لوڊ ڪرڻ لاءِ هڪ تصوير فائل چونڊيو.",
            "upload_failed": "تصوير اپ لوڊ ٿيڻ ۾ ناڪام. مهرباني ڪري ٻيهر ڪوشش ڪريو.",
            "network_error_upload": "تصوير اپ لوڊ ڪرڻ دوران نيٽ ورڪ غلطي پيش آئي.",
            "delete_failed": "تصوير ختم ڪرڻ ۾ ناڪامي.",
            "primary_failed": "بنيادي تصوير مقرر ڪرڻ ۾ ناڪامي."
        },
        "marketplace": {
            "catalog_primary_photo": "ڪيٽلاگ بنيادي تصوير",
            "thumbnail_n": "ٿمب نيل {{n}}",
            "no_photos_uploaded": "هن فصل لاٽ لاءِ ڪا تصوير اپ لوڊ نه ڪئي وئي آهي"
        }
    },
    "ne": {
        "dashboard": {
            "produce_photos_title": "उपज लटको तस्बिरहरू",
            "photo_limits_guidance": "अधिकतम १० तस्बिरहरू, प्रत्येक ५ MB (JPEG, PNG, WebP)",
            "current_photos_label": "हालका तस्बिरहरू:",
            "make_primary_photo": "मुख्य तस्बिर बनाउनुहोस्",
            "primary_photo_badge": "मुख्य",
            "photos_to_upload_label": "अपलोड गरिने तस्बिरहरू:",
            "set_primary": "मुख्य सेट गर्नुहोस्",
            "add_first_photos": "बालीका तस्बिरहरू छान्नुहोस् वा खिच्नुहोस्",
            "add_more_photos": "थप तस्बिरहरू थप्नुहोस् ({{remaining}} बाँकी)",
            "confirm_delete_photo": "के तपाईं निश्चित रूपमा यो सूचीकरणबाट यो तस्बिर हटाउन चाहनुहुन्छ?",
            "image_uploaded_success": "तस्बिरहरू सफलतापूर्वक अपलोड गरियो।",
            "image_deleted_success": "तस्बिर सफलतापूर्वक हटाइयो।",
            "primary_thumbnail_updated": "मुख्य क्याटलग थम्बनेल अद्यावधिक गरियो।",
            "reorder_success": "तस्बिर प्रदर्शन क्रम अद्यावधिक गरियो।",
            "manage_photos_title": "उपज तस्बिरहरू व्यवस्थापन गर्नुहोस्",
            "photos_attached_count": "{{count}}/{{max}} तस्बिरहरू संलग्न छन्",
            "attached_photos_heading": "संलग्न उपज तस्बिरहरू ({{count}}/{{max}})",
            "no_photos_yet": "अहिलेसम्म कुनै तस्बिर संलग्न गरिएको छैन",
            "upload_photos_hint": "व्यावसायिक खरिदकर्ताहरूलाई आकर्षित गर्न आफ्नो बालीको स्पष्ट तस्बिरहरू अपलोड गर्नुहोस्।",
            "primary_thumbnail": "मुख्य थम्बनेल",
            "make_primary": "मुख्य बनाउनुहोस्",
            "catalog_display_photo": "क्याटलग प्रदर्शन तस्बिर",
            "move_earlier": "अगाडि सार्नुहोस्",
            "move_later": "पछाडि सार्नुहोस्",
            "delete_photo": "तस्बिर मेटाउनुहोस्",
            "upload_new_photo": "नयाँ तस्बिर अपलोड गर्नुहोस्",
            "set_as_primary": "मुख्य रूपमा सेट गर्नुहोस्",
            "image_spec_hint": "कुल अधिकतम १० तस्बिरहरू • प्रत्येक ५ MB • JPEG, PNG वा WebP",
            "upload_photo_btn": "तस्बिर अपलोड गर्नुहोस्"
        },
        "errors": {
            "image_limit_reached": "प्रति सूचीकरण अधिकतम १० तस्बिरहरूको सीमा सकिएको छ।",
            "image_size_exceeded": "तस्बिरको आकार ५ MB को सीमाभन्दा बढी छ।",
            "unsupported_image_format": "असमर्थित तस्बिर ढाँचा। कृपया JPEG, PNG वा WebP तस्बिर छान्नुहोस्।",
            "select_image_first": "कृपया अपलोड गर्नका लागि एउटा तस्बिर फाइल छान्नुहोस्।",
            "upload_failed": "तस्बिर अपलोड असफल भयो। कृपया पुन: प्रयास गर्नुहोस्।",
            "network_error_upload": "तस्बिर अपलोड गर्दा नेटवर्क त्रुटि देखा पर्यो।",
            "delete_failed": "तस्बिर मेटाउन असफल।",
            "primary_failed": "मुख्य तस्बिर तोक्न असफल।"
        },
        "marketplace": {
            "catalog_primary_photo": "क्याटलग मुख्य तस्बिर",
            "thumbnail_n": "थम्बनेल {{n}}",
            "no_photos_uploaded": "यो बाली लटको लागि कुनै तस्बिर अपलोड गरिएको छैन"
        }
    },
    "sa": {
        "dashboard": {
            "produce_photos_title": "उत्पादराशि-छायाचित्राणि",
            "photo_limits_guidance": "अधिकतमं १० चित्राणि, प्रत्येकं ५ MB (JPEG, PNG, WebP)",
            "current_photos_label": "विद्यमानानि छायाचित्राणि:",
            "make_primary_photo": "प्रधानचित्रं कुरुत",
            "primary_photo_badge": "प्रधानम्",
            "photos_to_upload_label": "आरोपणयोग्यानि छायाचित्राणि:",
            "set_primary": "प्रधानत्वेन योजयत",
            "add_first_photos": "शस्यचित्राणि चिनुत वा गृह्णीत",
            "add_more_photos": "अतिरिक्तानि चित्राणि योजयत ({{remaining}} अवशिष्टम्)",
            "confirm_delete_photo": "किं भवान् निश्चयेन सूच्याः इदं चित्रं निष्कासयितुम् इच्छति?",
            "image_uploaded_success": "छायाचित्राणि साफल्येन आरोपितानि।",
            "image_deleted_success": "चित्रं साफल्येन निष्कासितम्।",
            "primary_thumbnail_updated": "प्रधान-सूची-लघुचित्रम् अद्यतनं कृतम्।",
            "reorder_success": "चित्रप्रदर्शनक्रमः अद्यतनः कृतः।",
            "manage_photos_title": "उत्पादचित्राणां प्रबन्धनम्",
            "photos_attached_count": "{{count}}/{{max}} चित्राणि संलग्नानि",
            "attached_photos_heading": "संलग्नानि उत्पादचित्राणि ({{count}}/{{max}})",
            "no_photos_yet": "अद्यापि किमपि चित्रं न संलग्नम्",
            "upload_photos_hint": "वाणिज्यिकक्रेतॄन् आकर्षयितुं स्वशस्यस्य स्पष्टचित्राणि आरोपयत।",
            "primary_thumbnail": "प्रधानलघुचित्रम्",
            "make_primary": "प्रधानं कुरुत",
            "catalog_display_photo": "सूचीप्रदर्शनचित्रम्",
            "move_earlier": "पूर्वं चालयत",
            "move_later": "पश्चात् चालयत",
            "delete_photo": "चित्रं निष्कासयत",
            "upload_new_photo": "नूतनं चित्रम् आरोपयत",
            "set_as_primary": "प्रधानत्वेन स्थापयत",
            "image_spec_hint": "कुलम् अधिकतमं १० चित्राणि • प्रत्येकं ५ MB • JPEG, PNG वा WebP",
            "upload_photo_btn": "चित्रम् आरोपयत"
        },
        "errors": {
            "image_limit_reached": "प्रतिसूची अधिकतमं १० चित्राणां सीमा प्राप्ता।",
            "image_size_exceeded": "चित्रपरिमाणं ५ MB सीमाम् अतिक्रान्तम्।",
            "unsupported_image_format": "असमर्थितं चित्रप्रारूपम्। कृपया JPEG, PNG वा WebP चित्रं चिनुत।",
            "select_image_first": "कृपया आरोपणार्थं चित्रसञ्चिकां चिनुत।",
            "upload_failed": "चित्रारोपणं विफलम्। कृपया पुनः प्रयतताम्।",
            "network_error_upload": "चित्रारोपणे जालीयदोषः सञ्जातः।",
            "delete_failed": "चित्रनिष्कासने विफलम्।",
            "primary_failed": "प्रधानचित्रनिर्धारणे विफलम्।"
        },
        "marketplace": {
            "catalog_primary_photo": "सूचीप्रधानचित्रम्",
            "thumbnail_n": "लघुचित्रम् {{n}}",
            "no_photos_uploaded": "अस्मै उत्पादराशये किमपि चित्रं न आरोपितम्"
        }
    },
    "mai": {
        "dashboard": {
            "produce_photos_title": "उपज लोटक छायाचित्र",
            "photo_limits_guidance": "अधिकतम १० टा फोटो, प्रति फोटो ५ MB (JPEG, PNG, WebP)",
            "current_photos_label": "वर्तमान छायाचित्र:",
            "make_primary_photo": "मुख्य फोटो बनाउ",
            "primary_photo_badge": "मुख्य",
            "photos_to_upload_label": "अपलोड कएल जाए बला फोटो:",
            "set_primary": "मुख्य सेट करू",
            "add_first_photos": "फसलबारीक फोटो चुनू वा खींचू",
            "add_more_photos": "आरो फोटो जोड़ू ({{remaining}} शेष)",
            "confirm_delete_photo": "की अहाँ सचमुच एहिसभ सूची सँ ई फोटो हटाबय चाहैत छी?",
            "image_uploaded_success": "छायाचित्र सफलतापूर्वक अपलोड भेल।",
            "image_deleted_success": "फोटो सफलतापूर्वक हटाओल गेल।",
            "primary_thumbnail_updated": "मुख्य कैटलॉग थंबनेल अपडेट भेल।",
            "reorder_success": "फोटो प्रदर्शन क्रम अपडेट भेल।",
            "manage_photos_title": "उपज फोटोक प्रबंधन करू",
            "photos_attached_count": "{{count}}/{{max}} फोटो संलग्न अछि",
            "attached_photos_heading": "संलग्न उपज फोटो ({{count}}/{{max}})",
            "no_photos_yet": "एखन धरि कोनो फोटो संलग्न नहि अछि",
            "upload_photos_hint": "व्यापारिक खरीदारकें आकर्षित करबाक लेल अपन फसलक साफ फोटो अपलोड करू।",
            "primary_thumbnail": "मुख्य थंबनेल",
            "make_primary": "मुख्य बनाउ",
            "catalog_display_photo": "कैटलॉग प्रदर्शन फोटो",
            "move_earlier": "पहिने घसकाउ",
            "move_later": "पाछाँ घसकाउ",
            "delete_photo": "फोटो हटाउ",
            "upload_new_photo": "नबका फोटो अपलोड करू",
            "set_as_primary": "मुख्य रूपमे सेट करू",
            "image_spec_hint": "कुल अधिकतम १० टा फोटो • प्रत्येक ५ MB • JPEG, PNG वा WebP",
            "upload_photo_btn": "फोटो अपलोड करू"
        },
        "errors": {
            "image_limit_reached": "प्रति सूची अधिकतम १० फोटोक सीमा समाप्त भेल।",
            "image_size_exceeded": "फोटॉक आकार ५ MB सीमा सँ अधिक अछि।",
            "unsupported_image_format": "असमर्थित छवि प्रारूप। कृपा क' JPEG, PNG वा WebP फोटो चुनू।",
            "select_image_first": "कृपा क' अपलोड करबाक लेल फोटो चुनू।",
            "upload_failed": "फोटो अपलोड विफल भेल। कृपा क' पुन: प्रयास करू।",
            "network_error_upload": "फोटो अपलोड करबाक काल नेटवर्क त्रुटि भेल।",
            "delete_failed": "फोटो हटाबयमे विफल।",
            "primary_failed": "मुख्य छवि तय करबामे विफल।"
        },
        "marketplace": {
            "catalog_primary_photo": "कैटलॉग मुख्य फोटो",
            "thumbnail_n": "थंबनेल {{n}}",
            "no_photos_uploaded": "एहि उपज लोटक लेल कोनो फोटो अपलोड नहि कएल गेल अछि"
        }
    },
    "kok": {
        "dashboard": {
            "produce_photos_title": "उत्पाद लॉट छायाचित्रां",
            "photo_limits_guidance": "कमाल १० फोटो, दरएकाक ५ MB (JPEG, PNG, WebP)",
            "current_photos_label": "सध्याचीं छायाचित्रां:",
            "make_primary_photo": "मुखेल फोटो करा",
            "primary_photo_badge": "मुखेल",
            "photos_to_upload_label": "अपलोड करपाचीं छायाचित्रां:",
            "set_primary": "मुखेल सेट करा",
            "add_first_photos": "पिकाचीं छायाचित्रां वेचा वा काढा",
            "add_more_photos": "आनीक फोटो जोडा ({{remaining}} उरल्यात)",
            "confirm_delete_photo": "तुमी खरेंच ह्या वळेरींतल्यान हो फोटो काडून उडोवंक सोदतात?",
            "image_uploaded_success": "छायाचित्रां येಶಸ್वीपणान अपलोड जालीं।",
            "image_deleted_success": "फोटो येಶಸ್वीपणान काडून उडयला।",
            "primary_thumbnail_updated": "मुखेल कॅटलॉग थंबनेल अपडेट जालो।",
            "reorder_success": "फोटो प्रदर्शन क्रम अपडेट जालो।",
            "manage_photos_title": "उत्पाद फोटो व्यवस्थापीत करा",
            "photos_attached_count": "{{count}}/{{max}} फोटो जोडल्यात",
            "attached_photos_heading": "जोडिल्लीं उत्पाद छायाचित्रां ({{count}}/{{max}})",
            "no_photos_yet": "अजून मेरेन खंयचेच फोटो जोडिल्ले नात",
            "upload_photos_hint": "वेपारी खरेदीदारांक आकर्षित करपाक तुमच्या पिकाचे नितळ फोटो अपलोड करा.",
            "primary_thumbnail": "मुखेल थंबनेल",
            "make_primary": "मुखेल करा",
            "catalog_display_photo": "कॅटलॉग प्रदर्शन फोटो",
            "move_earlier": "पयलीं व्हरचें",
            "move_later": "उपरांत व्हरचें",
            "delete_photo": "फोटो काडून उडयात",
            "upload_new_photo": "नवो फोटो अपलोड करा",
            "set_as_primary": "मुखेल म्हणून सेट करा",
            "image_spec_hint": "एकूण कमाल १० फोटो • दरएकाक ५ MB • JPEG, PNG वा WebP",
            "upload_photo_btn": "फोटो अपलोड करा"
        },
        "errors": {
            "image_limit_reached": "दर वळेरीक कमाल १० फोटोंची मर्यादा भरल्या।",
            "image_size_exceeded": "फोटोचो आकार ५ MB चे मर्यादे परस व्हड आसा।",
            "unsupported_image_format": "असमर्थित प्रतिमा स्वरूप. उपकार करून JPEG, PNG वा WebP फोटो वेचा.",
            "select_image_first": "उपकार करून अपलोड करपाक फोटो फाइल वेचा.",
            "upload_failed": "फोटो अपलोड अपेसी जालें. उपकार करून परतून यत्न करा.",
            "network_error_upload": "फोटो अपलोड करताना नेटवर्क चूक जाली.",
            "delete_failed": "फोटो काडून उडोवपाक अपेस.",
            "primary_failed": "मुखेल प्रतिमा थारावपाक अपेस."
        },
        "marketplace": {
            "catalog_primary_photo": "कॅटलॉग मुखेल फोटो",
            "thumbnail_n": "थंबनेल {{n}}",
            "no_photos_uploaded": "ह्या उत्पाद लॉटा खातीर खंयचेच फोटो अपलोड केल्ले नात"
        }
    },
    "doi": {
        "dashboard": {
            "produce_photos_title": "फसल लाट दियां फोटो",
            "photo_limits_guidance": "बद्द शा बद्द १० फोटो, हर इक ५ MB (JPEG, PNG, WebP)",
            "current_photos_label": "मौजूदा फोटो:",
            "make_primary_photo": "मुक्ख फोटो बनाओ",
            "primary_photo_badge": "मुक्ख",
            "photos_to_upload_label": "अपलोड कीते जाने आले फोटो:",
            "set_primary": "मुक्ख सेट करो",
            "add_first_photos": "फसल दियां फोटो चुनो जां खिच्चो",
            "add_more_photos": "होर फोटो जोड़ो ({{remaining}} बाकी)",
            "confirm_delete_photo": "केह तुस सचमुच इस सूची चा एह फोटो हटाना चांह्दे ओ?",
            "image_uploaded_success": "फोटो कामयाबी कन्नै अपलोड होई गे।",
            "image_deleted_success": "फोटो कामयाबी कन्नै हटाई दित्ता गेआ।",
            "primary_thumbnail_updated": "मुक्ख कैटलॉग थंबनेल अपडेट होई गेआ।",
            "reorder_success": "फोटो प्रदर्शन क्रम अपडेट होई गेआ।",
            "manage_photos_title": "फसल फोटो प्रबंध करो",
            "photos_attached_count": "{{count}}/{{max}} फोटो जुड़े दे न",
            "attached_photos_heading": "जुड़े दे फसल फोटो ({{count}}/{{max}})",
            "no_photos_yet": "अज्जै तगर कोई फोटो नेईं जुड़े दा ऐ",
            "upload_photos_hint": "व्यापारिक खरीददारें गी आकॢशत करने लेई अपनी फसल दे साफ फोटो अपलोड करो।",
            "primary_thumbnail": "मुक्ख थंबनेल",
            "make_primary": "मुक्ख बनाओ",
            "catalog_display_photo": "कैटलॉग डिस्प्ले फोटो",
            "move_earlier": "पैह्ले करो",
            "move_later": "पिच्छे करो",
            "delete_photo": "फोटो हटाओ",
            "upload_new_photo": "नवां फोटो अपलोड करो",
            "set_as_primary": "मुक्ख तौर पर सेट करो",
            "image_spec_hint": "कुल बद्द शा बद्द १० फोटो • हर इक ५ MB • JPEG, PNG जां WebP",
            "upload_photo_btn": "फोटो अपलोड करो"
        },
        "errors": {
            "image_limit_reached": "प्रति सूची बद्द शा बद्द १० फोटोएं दी सीमा पूरी होई गेई ऐ।",
            "image_size_exceeded": "फोटो दा आकार ५ MB सीमा शा बद्द ऐ।",
            "unsupported_image_format": "असमर्थित छवि प्रारूप। कृपा करियै JPEG, PNG जां WebP फोटो चुनो।",
            "select_image_first": "कृपा करियै अपलोड करने लेई इक फोटो फाइल चुनो।",
            "upload_failed": "फोटो अपलोड असफल रेहा। कृपा करियै परतियै कोशिश करो।",
            "network_error_upload": "फोटो अपलोड करदे बेल्लै नेटवर्क खराबी आई।",
            "delete_failed": "फोटो हटाने चा असफल।",
            "primary_failed": "मुक्ख छवि तय करने चा असफल।"
        },
        "marketplace": {
            "catalog_primary_photo": "कैटलॉग मुक्ख फोटो",
            "thumbnail_n": "थंबनेल {{n}}",
            "no_photos_uploaded": "इस फसल लाट लेई कोई फोटो अपलोड नेईं कीती गेई ऐ"
        }
    },
    "brx": {
        "dashboard": {
            "produce_photos_title": "फसल लटनि सावगारिफोर",
            "photo_limits_guidance": "बांसिन १० सावगारिफोर, मोनफ्रोमबो ५ MB (JPEG, PNG, WebP)",
            "current_photos_label": "दासिम थानाय सावगारिफोर:",
            "make_primary_photo": "गाहाय सावगारी बानाय",
            "primary_photo_badge": "गाहाय",
            "photos_to_upload_label": "अपलोड खालामनांगौ सावगारिफोर:",
            "set_primary": "गाहाय हिसाबै फज'",
            "add_first_photos": "फसलनि सावगारी सायख' एबा ला",
            "add_more_photos": "बांसिन सावगारी सोदेਰ ({{remaining}} थालांबाय)",
            "confirm_delete_photo": "नोंथाङा थारैनो बे लिसथिंनिफ्राय बे सावगारीखौ बोखारनो सानदों नामा?",
            "image_uploaded_success": "सावगारिफोरा मोजाङै अपलोड जाबाय।",
            "image_deleted_success": "सावगारिखौ मोजाङै बोखारबाय।",
            "primary_thumbnail_updated": "गाहाय केटलग थाम्बनेल दानाय जाबाय।",
            "reorder_success": "सावगारी दिनथिफुल' फारिखौ दानाय जाबाय।",
            "manage_photos_title": "फसल सावगारिखौ सामलाय",
            "photos_attached_count": "{{count}}/{{max}} सावगारिफोर फोनांजाबबाय",
            "attached_photos_heading": "फोनांजाबनाय फसल सावगारिफोर ({{count}}/{{max}})",
            "no_photos_yet": "दासिमबो जेबो सावगारी फोनांजाबाखै",
            "upload_photos_hint": "फालांगियारि बायग्राफोरखौ बोनो थाखाय नोंथांनि फसलनि रोखा सावगारी अपलोड खालाम।",
            "primary_thumbnail": "गाहाय थाम्बनेल",
            "make_primary": "गाहाय खालाम",
            "catalog_display_photo": "केटलग दिनथिफुल' सावगारी",
            "move_earlier": "सिगां लां",
            "move_later": "उनाव लां",
            "delete_photo": "सावगारी बोखार",
            "upload_new_photo": "गोदान सावगारी अपलोड खालाम",
            "set_as_primary": "गाहाय हिसाबै फज'",
            "image_spec_hint": "गासै बांसिन १० सावगारिफोर • मोनफ्रोमबो ५ MB • JPEG, PNG एबा WebP",
            "upload_photo_btn": "सावगारी अपलोड खालाम"
        },
        "errors": {
            "image_limit_reached": "मोनफ्रोम लिसथिंआव बांसिन १० सावगारिनि सीमा सौहैबाय।",
            "image_size_exceeded": "सावगारिनि महரா ५ MB सीमाखौ बारबाय।",
            "unsupported_image_format": "मोजां नङै सावगारी फरमेट। अननानै JPEG, PNG एबा WebP सावगारी सायख'।",
            "select_image_first": "अननानै अपलोड खालामनो सावगारी सायख'।",
            "upload_failed": "सावगारी अपलोड खालामनो हायाखैमोन। अननानै फिन नाजा।",
            "network_error_upload": "सावगारी अपलोड खालामनायाव नेटवार्क गोरोन्थि जाबाय।",
            "delete_failed": "सावगारी बोखारनो हायाखै।",
            "primary_failed": "गाहाय सावगारी सायख'नो हायाखै।"
        },
        "marketplace": {
            "catalog_primary_photo": "केटलग गाहाय सावगारी",
            "thumbnail_n": "थाम्बनेल {{n}}",
            "no_photos_uploaded": "बे फसल लटनि थाखाय जेबो सावगारी अपलोड खालामाखै"
        }
    },
    "mni": {
        "dashboard": {
            "produce_photos_title": "পোত্থোক লটকী ফোতোগ্রাফশিং",
            "photo_limits_guidance": "খ্বাইদগী য়াম্না ১০, অমমমদা ৫ MB (JPEG, PNG, WebP)",
            "current_photos_label": "হৌজিক লৈরিবা ফোতোগ্রাফশিং:",
            "make_primary_photo": "মরুওইবা ফোতো ওন্থোকউ",
            "primary_photo_badge": "মরুওইবা",
            "photos_to_upload_label": "অপলোদ তৌগদবা ফোতোগ্রাফশিং:",
            "set_primary": "মরুওইবা ওইনা সেত তৌ",
            "add_first_photos": "লৌউ-শিংউগী ফোতো খনগৎলু নত্রগা লৌউ",
            "add_more_photos": "অতোপ্পা ফোতোশিং হাপচিল্লু ({{remaining}} লেমহৌরি)",
            "confirm_delete_photo": "নহাক্না লিস্টিং অসিদগী ফোতো অসি অচুম্বা ওইনা লৌথোকপা পাম্ব্রা?",
            "image_uploaded_success": "ফোতোগ্রাফশিং মাইপাক্না অপলোদ তৌখ্রে।",
            "image_deleted_success": "ফোতো মাইপাক্না মুথৎখ্রে।",
            "primary_thumbnail_updated": "মরুওইবা কেতালোগ থম্বনেল অপদেত তৌখ্রে।",
            "reorder_success": "ফোতো উৎলিবা মথং-মনাও অপদেত তৌখ্রে।",
            "manage_photos_title": "পোত্থোক্কী ফোতোশিং শেন্নউ",
            "photos_attached_count": "{{count}}/{{max}} ফোতোশিং শম্নরে",
            "attached_photos_heading": "শম্নরবা পোত্থোক্কী ফোতোশিং ({{count}}/{{max}})",
            "no_photos_yet": "হৌজিকফাওবা ফোতো অমত্তা শম্নদ্রি",
            "upload_photos_hint": "ললোন-ইতিক্কী লৈবশিং পুখৎনবা নহাক্কী পোত্থোক্কী শেংলবা ফোতোশিং অপলোদ তৌ।",
            "primary_thumbnail": "মরুওইবা থম্বনেল",
            "make_primary": "মরুওইবা ওন্থোকউ",
            "catalog_display_photo": "কেতালোগ দিপ্লে ফোতো",
            "move_earlier": "মাংলোইদা চিংশিল্লু",
            "move_later": "তুংলোইদা চিংশিল্লু",
            "delete_photo": "ফোতো মুথৎলু",
            "upload_new_photo": "অনৌবা ফোতো অপলোদ তৌ",
            "set_as_primary": "মরুওইবা ওইনা সেত তৌ",
            "image_spec_hint": "অপুনবা খ্বাইদগী য়াম্না ১০ • অমমমদা ৫ MB • JPEG, PNG নত্রগা WebP",
            "upload_photo_btn": "ফোতো অপলোদ তৌ"
        },
        "errors": {
            "image_limit_reached": "লিস্টিং অমদা খ্বাইদগী য়াম্না ফোতো ১০ গী সীমাদা য়ৌরে।",
            "image_size_exceeded": "ফোতোগী অপুনবা অসি ৫ MB সীমাদগী হেল্লে।",
            "unsupported_image_format": "য়াদবা ফোতো ফোর্মাত। চানবীদুনা JPEG, PNG নত্রগা WebP ফোতো খনগৎলু।",
            "select_image_first": "চানবীদুনা অপলোদ তৌনবা ফোতো ফাইল অমা খনগৎলু।",
            "upload_failed": "ফোতো অপলোদ তৌবা ঙমদ্রে। চানবীদুনা অমুক হন্না হোৎনবীয়ু।",
            "network_error_upload": "ফোতো অপলোদ তৌরিঙৈদা নেতৱার্ক্কী অশোয়বা থোকখ্রে।",
            "delete_failed": "ফোতো মুথৎপা ঙমদ্রে।",
            "primary_failed": "মরুওইবা ফোতো লেপপা ঙমদ্রে।"
        },
        "marketplace": {
            "catalog_primary_photo": "কেতালোগ মরুওইবা ফোতো",
            "thumbnail_n": "থম্বনেল {{n}}",
            "no_photos_uploaded": "পোত্থোক লত অসিগী ফোতো অমত্তা অপলোদ তৌদ্রি"
        }
    },
    "sat": {
        "dashboard": {
            "produce_photos_title": "ᱩᱯᱚᱡᱽ ᱞᱚᱴ ᱨᱮᱱᱟᱜ ᱪᱤᱛᱟᱹᱨ",
            "photo_limits_guidance": "ᱡᱟᱹᱥᱛᱤ ᱠᱷᱚᱱ ᱡᱟᱹᱥᱛᱤ ᱑᱐ ᱪᱤᱛᱟᱹᱨ, ᱢᱤᱫ-ᱢᱤᱫᱴᱟᱝ ᱕ MB (JPEG, PNG, WebP)",
            "current_photos_label": "ᱱᱤᱛᱚᱜᱟᱜ ᱪᱤᱛᱟᱹᱨ:",
            "make_primary_photo": "ᱢᱩᱬᱩᱛ ᱪᱤᱛᱟᱹᱨ ᱵᱮᱱᱟᱣ ᱢᱮ",
            "primary_photo_badge": "ᱢᱩᱬᱩᱛ",
            "photos_to_upload_label": "ᱟᱯᱞᱳᱰ ᱞᱟᱹᱜᱤᱫ ᱪᱤᱛᱟᱹᱨ:",
            "set_primary": "ᱢᱩᱬᱩᱛ ᱞᱮᱠᱟᱛᱮ ᱥᱟᱡᱟᱣ ᱢᱮ",
            "add_first_photos": "ᱟᱨᱡᱟᱣ ᱪᱤᱛᱟᱹᱨ ᱵᱟᱪᱷᱟᱣ ᱢᱮ ᱥᱮ ᱛᱩᱞᱟᱹᱣ ᱢᱮ",
            "add_more_photos": "ᱟᱨᱦᱚᱸ ᱪᱤᱛᱟᱹᱨ ᱥᱮᱞᱮᱫᱽ ᱢᱮ ({{remaining}} ᱥᱟᱨᱮᱡ ᱢᱮᱱᱟᱜ-ᱟ)",
            "confirm_delete_photo": "ᱪᱮᱫ ᱟᱢ ᱱᱚᱶᱟ ᱛᱟᱹᱞᱠᱟᱹ ᱠᱷᱚᱱ ᱱᱚᱶᱟ ᱪᱤᱛᱟᱹᱨ ᱚᱪᱚᱜ ᱥᱟᱱᱟᱭᱮᱫ ᱢᱮᱭᱟ?",
            "image_uploaded_success": "ᱪᱤᱛᱟᱹᱨ ᱱᱟᱯᱟᱭ ᱛᱮ ᱟᱯᱞᱳᱰ ᱮᱱᱟ।",
            "image_deleted_success": "ᱪᱤᱛᱟᱹᱨ ᱱᱟᱯᱟᱭ ᱛᱮ ᱚᱪᱚᱜ ᱮᱱᱟ।",
            "primary_thumbnail_updated": "ᱢᱩᱬᱩᱛ ᱠᱮᱴᱞᱚᱜᱽ ᱛᱷᱟᱢᱵᱽᱱᱮᱞ ᱦᱟᱹᱞᱤᱭᱟᱹᱠ ᱮᱱᱟ।",
            "reorder_success": "ᱪᱤᱛᱟᱹᱨ ᱩᱫᱩᱜ ᱨᱮᱱᱟᱜ ᱞᱟᱦᱟ-ᱛᱟᱭᱚᱢ ᱦᱟᱹᱞᱤᱭᱟᱹᱠ ᱮᱱᱟ।",
            "manage_photos_title": "ᱩᱯᱚᱡᱽ ᱪᱤᱛᱟᱹᱨ ᱠᱚ ᱥᱟᱢᱵᱽᱲᱟᱣ ᱢᱮ",
            "photos_attached_count": "{{count}}/{{max}} ᱪᱤᱛᱟᱹᱨ ᱡᱚᱲᱟᱣ ᱮᱱᱟ",
            "attached_photos_heading": "ᱡᱚᱲᱟᱣ ᱟᱠᱟᱱ ᱩᱯᱚᱡᱽ ᱪᱤᱛᱟᱹᱨ ({{count}}/{{max}})",
            "no_photos_yet": "ᱱᱤᱛ ᱫᱷᱟᱹᱵᱤᱡ ᱪᱮᱫ ᱪᱤᱛᱟᱹᱨ ᱦᱚᱸ ᱵᱟᱝ ᱡᱚᱲᱟᱣ ᱟᱠᱟᱱᱟ",
            "upload_photos_hint": "ᱵᱮᱯᱟᱨᱤᱭᱟᱹ ᱠᱤᱨᱤᱧᱤᱭᱟᱹ ᱠᱚ ᱟᱠᱚᱨᱥᱚᱱ ᱞᱟᱹᱜᱤᱫ ᱟᱢᱟᱜ ᱟᱨᱡᱟᱣ ᱨᱮᱱᱟᱜ ᱥᱟᱯᱷᱟ ᱪᱤᱛᱟᱹᱨ ᱟᱯᱞᱳᱰ ᱢᱮ।",
            "primary_thumbnail": "ᱢᱩᱬᱩᱛ ᱛᱷᱟᱢᱵᱽᱱᱮᱞ",
            "make_primary": "ᱢᱩᱬᱩᱛ ᱵᱮᱱᱟᱣ ᱢᱮ",
            "catalog_display_photo": "ᱠᱮᱴᱞᱚᱜᱽ ᱩᱫᱩᱜ ᱪᱤᱛᱟᱹᱨ",
            "move_earlier": "ᱞᱟᱦᱟ ᱥᱮᱫ ᱤᱫᱤ ᱢᱮ",
            "move_later": "ᱛᱟᱭᱚᱢ ᱥᱮᱫ ᱤᱫᱤ ᱢᱮ",
            "delete_photo": "ᱪᱤᱛᱟᱹᱨ ᱚᱪᱚᱜ ᱢᱮ",
            "upload_new_photo": "ᱱᱟᱶᱟ ᱪᱤᱛᱟᱹᱨ ᱟᱯᱞᱳᱰ ᱢᱮ",
            "set_as_primary": "ᱢᱩᱬᱩᱛ ᱞᱮᱠᱟᱛᱮ ᱥᱟᱡᱟᱣ ᱢᱮ",
            "image_spec_hint": "ᱜᱩᱴ ᱡᱟᱹᱥᱛᱤ ᱠᱷᱚᱱ ᱡᱟᱹᱥᱛᱤ ᱑᱐ ᱪᱤᱛᱟᱹᱨ • ᱢᱤᱫ-ᱢᱤᱫᱴᱟᱝ ᱕ MB • JPEG, PNG ᱥᱮ WebP",
            "upload_photo_btn": "ᱪᱤᱛᱟᱹᱨ ᱟᱯᱞᱳᱰ ᱢᱮ"
        },
        "errors": {
            "image_limit_reached": "ᱢᱤᱫᱴᱟᱝ ᱛᱟᱹᱞᱠᱟᱹ ᱨᱮ ᱡᱟᱹᱥᱛᱤ ᱠᱷᱚᱱ ᱡᱟᱹᱥᱛᱤ ᱑᱐ ᱪᱤᱛᱟᱹᱨ ᱨᱮᱱᱟᱜ ᱥᱤᱢᱟᱹ ᱯᱩᱨᱟᱹᱣ ᱮᱱᱟ।",
            "image_size_exceeded": "ᱪᱤᱛᱟᱹᱨ ᱨᱮᱱᱟᱜ ᱢᱟᱯ ᱕ MB ᱥᱤᱢᱟᱹ ᱠᱷᱚᱱ ᱵᱟᱹᱲᱛᱤ ᱜᱮᱭᱟ।",
            "unsupported_image_format": "ᱵᱟᱝ ᱥᱟᱦᱟᱣᱟᱜ ᱪᱤᱛᱟᱹᱨ ᱯᱷᱚᱨᱢᱮᱴ। ᱫᱟᱭᱟ ᱠᱟᱛᱮ JPEG, PNG ᱥᱮ WebP ᱪᱤᱛᱟᱹᱨ ᱵᱟᱪᱷᱟᱣ ᱢᱮ।",
            "select_image_first": "ᱫᱟᱭᱟ ᱠᱟᱛᱮ ᱟᱯᱞᱳᱰ ᱞᱟᱹᱜᱤᱫ ᱢᱤᱫᱴᱟᱝ ᱪᱤᱛᱟᱹᱨ ᱵᱟᱪᱷᱟᱣ ᱢᱮ।",
            "upload_failed": "ᱪᱤᱛᱟᱹᱨ ᱟᱯᱞᱳᱰ ᱵᱟᱝ ᱦᱩᱭ ᱞᱮᱱᱟ। ᱫᱟᱭᱟ ᱠᱟᱛᱮ ᱟᱨᱦᱚᱸ ᱪᱮᱥᱴᱟᱭ ᱢᱮ।",
            "network_error_upload": "ᱪᱤᱛᱟᱹᱨ ᱟᱯᱞᱳᱰ ᱡᱚᱠᱷᱟᱜ ᱱᱮᱴᱣᱟᱨᱠ ᱵᱷᱩᱞ ᱦᱩᱭ ᱮᱱᱟ।",
            "delete_failed": "ᱪᱤᱛᱟᱹᱨ ᱚᱪᱚᱜ ᱵᱟᱝ ᱦᱩᱭ ᱞᱮᱱᱟ।",
            "primary_failed": "ᱢᱩᱬᱩᱛ ᱪᱤᱛᱟᱹᱨ ᱴᱷᱟᱹᱣᱠᱟᱹ ᱵᱟᱝ ᱦᱩᱭ ᱞᱮᱱᱟ।"
        },
        "marketplace": {
            "catalog_primary_photo": "ᱠᱮᱴᱞᱚᱜᱽ ᱢᱩᱬᱩᱛ ᱪᱤᱛᱟᱹᱨ",
            "thumbnail_n": "ᱛᱷᱟᱢᱵᱽᱱᱮᱞ {{n}}",
            "no_photos_uploaded": "ᱱᱚᱶᱟ ᱩᱯᱚᱡᱽ ᱞᱚᱴ ᱞᱟᱹᱜᱤᱫ ᱪᱮᱫ ᱪᱤᱛᱟᱹᱨ ᱦᱚᱸ ᱵᱟᱝ ᱟᱯᱞᱳᱰ ᱟᱠᱟᱱᱟ"
        }
    }
}

EXPECTED_DASHBOARD_KEYS = [
    "produce_photos_title", "photo_limits_guidance", "current_photos_label", "make_primary_photo",
    "primary_photo_badge", "photos_to_upload_label", "set_primary", "add_first_photos",
    "add_more_photos", "confirm_delete_photo", "image_uploaded_success", "image_deleted_success",
    "primary_thumbnail_updated", "reorder_success", "manage_photos_title", "photos_attached_count",
    "attached_photos_heading", "no_photos_yet", "upload_photos_hint", "primary_thumbnail",
    "make_primary", "catalog_display_photo", "move_earlier", "move_later", "delete_photo",
    "upload_new_photo", "set_as_primary", "image_spec_hint", "upload_photo_btn"
]

EXPECTED_ERROR_KEYS = [
    "image_limit_reached", "image_size_exceeded", "unsupported_image_format",
    "select_image_first", "upload_failed", "network_error_upload", "delete_failed", "primary_failed"
]

EXPECTED_MARKETPLACE_KEYS = [
    "catalog_primary_photo", "thumbnail_n", "no_photos_uploaded"
]

INTERPOLATION_VARS = {
    "add_more_photos": ["{{remaining}}"],
    "photos_attached_count": ["{{count}}", "{{max}}"],
    "attached_photos_heading": ["{{count}}", "{{max}}"],
    "thumbnail_n": ["{{n}}"],
}


def populate_locales():
    """Populate 21 languages with their corresponding dictionaries."""
    for loc, trans in TRANSLATIONS.items():
        loc_dir = LOCALES_DIR / loc
        if not loc_dir.exists():
            print(f"Warning: Directory {loc_dir} does not exist!")
            continue

        # 1. dashboard.json
        d_file = loc_dir / "dashboard.json"
        if d_file.exists():
            d_data = json.loads(d_file.read_text(encoding="utf-8"))
            d_data.update(trans["dashboard"])
            d_file.write_text(json.dumps(d_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # 2. errors.json
        e_file = loc_dir / "errors.json"
        if e_file.exists():
            e_data = json.loads(e_file.read_text(encoding="utf-8"))
            e_data.update(trans["errors"])
            e_file.write_text(json.dumps(e_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        # 3. marketplace.json
        m_file = loc_dir / "marketplace.json"
        if m_file.exists():
            m_data = json.loads(m_file.read_text(encoding="utf-8"))
            m_data.update(trans["marketplace"])
            m_file.write_text(json.dumps(m_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Successfully populated {len(TRANSLATIONS)} languages.")


def verify_all_23_languages():
    """Strictly verify key presence, JSON syntax, and interpolation placeholders in all 23 languages."""
    locales = sorted([d.name for d in LOCALES_DIR.iterdir() if d.is_dir()])
    assert len(locales) == 23, f"Expected 23 locales, found {len(locales)}: {locales}"

    total_checked = 0
    errors = []

    for loc in locales:
        d_file = LOCALES_DIR / loc / "dashboard.json"
        e_file = LOCALES_DIR / loc / "errors.json"
        m_file = LOCALES_DIR / loc / "marketplace.json"

        # Check files exist
        for f, name in [(d_file, "dashboard.json"), (e_file, "errors.json"), (m_file, "marketplace.json")]:
            if not f.exists():
                errors.append(f"[{loc}] Missing file {name}")
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception as ex:
                errors.append(f"[{loc}] Corrupt JSON in {name}: {ex}")

        # Check dashboard keys
        d_data = json.loads(d_file.read_text(encoding="utf-8"))
        for k in EXPECTED_DASHBOARD_KEYS:
            total_checked += 1
            if k not in d_data:
                errors.append(f"[{loc}/dashboard.json] Missing key '{k}'")
            else:
                val = d_data[k]
                if not isinstance(val, str) or not val.strip():
                    errors.append(f"[{loc}/dashboard.json] Empty or invalid value for key '{k}'")
                if k in INTERPOLATION_VARS:
                    for var in INTERPOLATION_VARS[k]:
                        if var not in val:
                            errors.append(f"[{loc}/dashboard.json] Missing placeholder {var} in key '{k}' (value: '{val}')")

        # Check error keys
        e_data = json.loads(e_file.read_text(encoding="utf-8"))
        for k in EXPECTED_ERROR_KEYS:
            total_checked += 1
            if k not in e_data:
                errors.append(f"[{loc}/errors.json] Missing key '{k}'")
            else:
                val = e_data[k]
                if not isinstance(val, str) or not val.strip():
                    errors.append(f"[{loc}/errors.json] Empty or invalid value for key '{k}'")

        # Check marketplace keys
        m_data = json.loads(m_file.read_text(encoding="utf-8"))
        for k in EXPECTED_MARKETPLACE_KEYS:
            total_checked += 1
            if k not in m_data:
                errors.append(f"[{loc}/marketplace.json] Missing key '{k}'")
            else:
                val = m_data[k]
                if not isinstance(val, str) or not val.strip():
                    errors.append(f"[{loc}/marketplace.json] Empty or invalid value for key '{k}'")
                if k in INTERPOLATION_VARS:
                    for var in INTERPOLATION_VARS[k]:
                        if var not in val:
                            errors.append(f"[{loc}/marketplace.json] Missing placeholder {var} in key '{k}' (value: '{val}')")

    print(f"Verified {total_checked} keys across 23 languages.")
    if errors:
        print(f"FAILED: Found {len(errors)} parity errors:")
        for err in errors[:20]:
            print("  -", err)
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors")
        sys.exit(1)
    else:
        print("ALL 23 LANGUAGES PASSED 100% PARITY AUDIT! Zero missing keys, zero placeholder errors.")


if __name__ == "__main__":
    populate_locales()
    verify_all_23_languages()
