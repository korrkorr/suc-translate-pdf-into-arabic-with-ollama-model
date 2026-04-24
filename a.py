import pymupdf
import requests
import json
import time

# Define color white as RGB tuple
WHITE = (1, 1, 1)

# This flag ensures that text will be dehyphenated after extraction.
textflags = pymupdf.TEXT_DEHYPHENATE

# Ollama configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "translategemma:12b"  # يمكن تغييره إلى أي نموذج متوفر لديك

def translate_with_ollama(text, max_retries=3):
    """ترجمة النص باستخدام Ollama"""
    if not text or len(text.strip()) < 5:
        return text
    
    # تحضير الـ prompt للترجمة
    prompt = f"""Translate the following English text to Arabic. Return ONLY the Arabic translation, no explanations or additional text.

English: {text}

Arabic:"""
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json().get("response", "").strip()
                # تنظيف النتيجة من أي اقتباسات أو بادئات
                result = result.strip('"\'')
                # إزالة أي نص إضافي مثل "Arabic translation:"
                if "Arabic:" in result:
                    result = result.split("Arabic:")[-1].strip()
                if "الترجمة:" in result:
                    result = result.split("الترجمة:")[-1].strip()
                
                return result if result else text
            else:
                print(f"خطأ في الترجمة: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"محاولة {attempt + 1}: انتهى الوقت")
        except requests.exceptions.ConnectionError:
            print(f"محاولة {attempt + 1}: فشل الاتصال بـ Ollama")
        except Exception as e:
            print(f"محاولة {attempt + 1}: خطأ - {e}")
        
        if attempt < max_retries - 1:
            time.sleep(2)  # انتظار قبل إعادة المحاولة
    
    return text  # إرجاع النص الأصلي في حالة الفشل

# Open the document
doc = pymupdf.open("1_1-5.pdf")

# Define an Optional Content layer in the document named "Arabic"
ocg_xref = doc.add_ocg("Arabic", on=True)

# Iterate over all pages
for page_num, page in enumerate(doc, 1):
    print(f"\nجاري معالجة الصفحة {page_num}...")
    
    # Extract text grouped like lines in a paragraph.
    blocks = page.get_text("blocks", flags=textflags)
    total_blocks = len(blocks)
    
    # Every block of text is contained in a rectangle ("bbox")
    for idx, block in enumerate(blocks, 1):
        bbox = block[:4]  # area containing the text
        english = block[4]  # the text of this block
        
        # تجاهل النصوص القصيرة جداً أو التي تحتوي على أرقام فقط
        if len(english.strip()) < 10:
            continue
            
        print(f"  ترجمة النص {idx}/{total_blocks}: {english[:50]}...")
        
        # Translate the text using Ollama
        arabic = translate_with_ollama(english)
        
        # Cover the English text with a white rectangle
        page.draw_rect(bbox, color=None, fill=WHITE, oc=ocg_xref)
        
        # Write the Arabic text into the rectangle
        page.insert_htmlbox(bbox, arabic, oc=ocg_xref)
        
        # تأخير بسيط لتجنب إرهاق خادم Ollama
        time.sleep(0.5)

# Save the translated document
doc.save("book_arabic.pdf")
print("\n✅ تم حفظ الكتاب المترجم في: book_arabic.pdf")
