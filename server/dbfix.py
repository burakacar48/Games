import sqlite3

def fix_character_encoding():
    """
    Veritabanındaki 'games' ve 'categories' tablolarındaki 
    bozuk Türkçe karakterleri düzeltir.
    """
    # Düzeltme haritası: 'Bozuk Karakter': 'Doğru Karakter'
    char_map = {
        'Ä±': 'ı', 'ÄŸ': 'ğ', 'Ä°': 'İ', 'Ã¼': 'ü', 'ÅŸ': 'ş',
        'Ã¶': 'ö', 'Ã§': 'ç', 'Äž': 'Ğ', 'Ãœ': 'Ü', 'Åž': 'Ş',
        'Ã–': 'Ö', 'Ã‡': 'Ç',
        'Ä±': 'ı', 'ÄŸ': 'ğ', 'Ä°': 'İ', 'Ã¼': 'ü', 'ÅŸ': 'ş',
        'Ã¶': 'ö', 'Ã§': 'ç', 'Äž': 'Ğ', 'Ãœ': 'Ü', 'Åž': 'Ş',
        'Ã–': 'Ö', 'Ã‡': 'Ç',
        'ÅŸ': 'ş', 'ÄŸ': 'ğ', 'Ä±': 'ı', 'Ã§': 'ç', 'Ã¶': 'ö', 'Ã¼': 'ü',
        'Åž': 'Ş', 'Äž': 'Ğ', 'Ä°': 'İ', 'Ã‡': 'Ç', 'Ã–': 'Ö', 'Ãœ': 'Ü'
    }

    try:
        conn = sqlite3.connect('kafe.db')
        cursor = conn.cursor()

        tables_to_fix = {
            'categories': ['name'],
            'games': ['oyun_adi', 'aciklama']
        }

        total_updated_rows = 0

        for table, columns in tables_to_fix.items():
            print(f"\n'{table}' tablosu işleniyor...")
            # Sadece ilgili sütunları seç
            cursor.execute(f"SELECT id, {', '.join(columns)} FROM {table}")
            rows = cursor.fetchall()

            updated_count_per_table = 0

            for row in rows:
                row_id = row[0]
                needs_update = False
                new_values = []

                # Her bir sütundaki metni kontrol et
                for i, col_text in enumerate(row[1:]):
                    if not isinstance(col_text, str):
                        new_values.append(col_text)
                        continue

                    original_text = col_text
                    fixed_text = original_text
                    for bad, good in char_map.items():
                        fixed_text = fixed_text.replace(bad, good)

                    new_values.append(fixed_text)

                    if original_text != fixed_text:
                        needs_update = True
                        print(f"  ID {row_id}: '{original_text[:30]}...' -> '{fixed_text[:30]}...'")

                # Eğer en az bir sütunda değişiklik yapıldıysa, satırı güncelle
                if needs_update:
                    set_clause = ", ".join([f"{col} = ?" for col in columns])
                    new_values.append(row_id)
                    cursor.execute(f"UPDATE {table} SET {set_clause} WHERE id = ?", tuple(new_values))
                    updated_count_per_table += 1

            if updated_count_per_table > 0:
                print(f"'{table}' tablosunda {updated_count_per_table} satır güncellendi.")
                total_updated_rows += updated_count_per_table

        conn.commit()
        conn.close()

        if total_updated_rows > 0:
            print(f"\nToplam {total_updated_rows} satır başarıyla güncellendi.")
        else:
            print("\nDüzeltilecek bir veri bulunamadı. Karakterler zaten doğru olabilir.")

    except sqlite3.Error as e:
        print(f"Veritabanı hatası: {e}")
    except Exception as e:
        print(f"Beklenmedik bir hata oluştu: {e}")

if __name__ == '__main__':
    fix_character_encoding()