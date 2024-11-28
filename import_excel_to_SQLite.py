import sqlite3
import pandas as pd  # Убедитесь, что эта библиотека импортирована
from app import cursor, conn
import re

def import_excel_to_db(file_path):
    df = pd.read_excel(file_path, sheet_name=0)  # Загружаем данные из первого листа Excel-файла

    for index, row in df.iterrows():
        # Настройка столбцов
        name = row['Name']  # Название товара
        price = row['Price']  # Цена
        product_id = row['Product ID']  # ID товара
        numeric_price_match = re.search(r'\d+(\.\d+)?', str(price))  # Извлечение числовой части

        if numeric_price_match:
            numeric_price = float(numeric_price_match.group())  # Преобразование в число
        else:
            print(f"Некорректное значение цены в строке {index + 1}: {price}")
            continue

        product_id = row['Product ID']  # ID товара
        
        # Проверка данных
        if pd.isna(name) or pd.isna(price) or pd.isna(product_id):
            print(f"Пропущена строка {index + 1}: данные отсутствуют (Name='{name}', Price='{price}', Product ID='{product_id}')")
            continue

        try:
            # Добавление данных в базу
            cursor.execute(
                '''INSERT INTO products (name, price, product_id) VALUES (?, ?, ?)''', 
                (name, numeric_price, product_id)
            )
            print(name, price, product_id)
        except sqlite3.IntegrityError as e:
            print(f"Ошибка при добавлении строки {index + 1}: {e}")
            continue

    conn.commit()
    print("Данные успешно импортированы из Excel!")


if __name__ == "__main__":
    import_excel_to_db('Kirputori_30.11.xlsx')