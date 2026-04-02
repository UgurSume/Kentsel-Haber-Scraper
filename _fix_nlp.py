"""Script: rewrites extract_location in nlp_service.py with correct priority."""
import re

PATH = r'C:\Users\ugurs\OneDrive\Masaüstü\kentsel-haber-scraper\backend\src\services\nlp_service.py'

NEW_FUNC = '''\
    def extract_location(self, text: str) -> Optional[str]:
        """
        Metinden konum bilgisi çıkarır.
        Öncelik sırası:
        1. Sokak / cadde / bulvar (en spesifik)
        2. Mahalle / köy / site
        3. İlçe adları
        4. spaCy ile adlı varlık tanıma (NER)
        5. İl düzeyi geri dönüş: Kocaeli
        """
        if not text:
            return None

        text = text.strip()

        _STOP = {'bir', 'bu', 'şu', 'o', 've', 'ile', 'da', 'de', 'ta', 'te', 'ki', 'mi'}

        def _clean(s: str):
            s = s.strip()
            return None if (len(s) < 3 or s.lower() in _STOP) else s

        # Yöntem 1: Sokak / cadde / bulvar (en spesifik adres)
        sokak_patterns = [
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:Sokağı|Sokak|Sk\.)',
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:Caddesi|Cadde|Cd\.)',
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:Bulvarı|Bulvar|Blv\.)',
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:adresinde|mevkiinde)',
        ]
        for pattern in sokak_patterns:
            match = re.search(pattern, text)
            if match and _clean(match.group(1)):
                return match.group(0).strip()

        # Yöntem 2: Mahalle / köy / site
        mahalle_patterns = [
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:Mahallesi|Mahalle|Mah\.)',
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:Köyü|Köy)',
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:Sitesi|Site)',
            r'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ\s]{1,30}?)\s+(?:semtinde|bölgesinde)',
        ]
        for pattern in mahalle_patterns:
            match = re.search(pattern, text)
            if match and _clean(match.group(1)):
                return match.group(0).strip()

        # Yöntem 3: İlçe adlarını ara (Türkçe eklerle — "Gebzede", "İzmit\'te")
        for district in self.districts:
            pattern = rf\'(?<![a-zA-ZçğışöüÇĞİÖŞÜ]){re.escape(district)}\'
            if re.search(pattern, text, re.IGNORECASE):
                return district

        # Yöntem 3b: Hal eki kalıpları ("Gebze\'de", "Körfez\'de")
        hal_patterns = [
            r\'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ]+)\\\'(?:de|da|te|ta|nde|nda|nin|nın|nun|nün)\\b\',
            r\'([A-ZÇĞİÖŞÜ][a-zçğışöüA-ZÇĞİÖŞÜ]+)\\s+ilçes\',
        ]
        for pattern in hal_patterns:
            matches = re.findall(pattern, text)
            if matches:
                location = matches[0].strip()
                for district in self.districts:
                    if district.lower() in location.lower():
                        return district

        # Yöntem 4: spaCy varsa adlı varlık tanıma (NER) kullan
        if self.spacy_model:
            try:
                doc = self.spacy_model(text[:1000])
                for ent in doc.ents:
                    if ent.label_ in [\'LOC\', \'GPE\']:
                        for district in self.districts:
                            if district.lower() in ent.text.lower():
                                return district
                        return ent.text
            except Exception as e:
                logger.error(f"İsimli varlık tanıma hatası: {e}")

        # Yöntem 5: İl düzeyi geri dönüş — metinde "Kocaeli" geçiyorsa
        if re.search(r\'(?<![a-zA-ZçğışöüÇĞİÖŞÜ])Kocaeli\', text, re.IGNORECASE):
            return "Kocaeli"

        return None\
'''

with open(PATH, encoding='utf-8') as f:
    content = f.read()

# Find start marker
START = '    def extract_location(self, text: str) -> Optional[str]:'
# Find end marker (the next method at same indent level)
END = '    def clean_content(self, html_content: str) -> str:'

start_idx = content.index(START)
end_idx = content.index(END)

new_content = content[:start_idx] + NEW_FUNC + '\n\n' + content[end_idx:]

with open(PATH, 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Done. Verifying...')
with open(PATH, encoding='utf-8') as f:
    verify = f.read()
assert 'Yöntem 1: Sokak / cadde / bulvar' in verify
assert 'Yöntem 2: Mahalle / köy / site' in verify
assert 'Yöntem 3: İlçe' in verify
print('OK')
