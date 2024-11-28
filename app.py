import sqlite3
import pandas as pd
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)

# Connect to SQLite database (creates a new database file if it doesn't exist)
conn = sqlite3.connect("store.db", check_same_thread=False)
cursor = conn.cursor()

try:
    cursor.execute('ALTER TABLE products ADD COLUMN customer_id TEXT DEFAULT NULL;')
    conn.commit()
except sqlite3.OperationalError:
    # Столбец уже существует
    pass


# Create table for products
cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    price REAL NOT NULL,
    product_id TEXT UNIQUE NOT NULL
);
''')

# Create table for customers
cursor.execute('''
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT UNIQUE NOT NULL
);
''')

# Create table for purchases
cursor.execute('''
CREATE TABLE IF NOT EXISTS purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    customer_id TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);
''')

# Import data from Excel
def import_excel_to_db(file_path):
    df = pd.read_excel(file_path, sheet_name=0)  # Assuming the first sheet contains the data
    
    for index, row in df.iterrows():
        name = row.iloc[0]  # First column: product name
        price = row.iloc[1]  # Second column: price
        
        # Handle missing or invalid data
        if pd.isna(name) or pd.isna(price):
            print(f"Skipping row {index + 1} due to missing data: Name='{name}', Price='{price}'")
            continue

        product_id = f"{index + 1}b"  # Generate product ID
        cursor.execute('''INSERT INTO products (name, price, product_id) VALUES (?, ?, ?)''', (name, price, product_id))
    
    conn.commit()
    print("Data imported successfully from Excel!")

# Flask routes
@app.route('/')
def home():
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return render_template('index.html', products=products)

@app.route('/add_product', methods=['POST'])
def add_product():
    name = request.form['name']
    price = request.form['price']
    product_id = request.form['product_id']

    try:
        # Найти максимальный текущий ID
        cursor.execute('SELECT MAX(id) FROM products')
        max_id = cursor.fetchone()[0] or 0  # Если таблица пуста, начать с 0
        new_id = max_id + 1

        # Добавить продукт с вручную рассчитанным ID
        cursor.execute('''INSERT INTO products (id, name, price, product_id) VALUES (?, ?, ?, ?)''',
                       (new_id, name, float(price), product_id))
        conn.commit()
        return jsonify({"success": True, "message": "Product added successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    try:
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()

        # Пересчитать ID, чтобы они были последовательными
        cursor.execute('''
            UPDATE products
            SET id = (
                SELECT COUNT(*) + 1
                FROM (SELECT * FROM products AS sub WHERE sub.id < products.id)
            )
        ''')
        conn.commit()
        return jsonify({"success": True, "message": "Product deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/calculate_total/<string:customer_id>', methods=['GET'])
def calculate_total(customer_id):
    try:
        cursor.execute("SELECT SUM(price) FROM products WHERE customer_id = ?", (customer_id,))
        total = cursor.fetchone()[0] or 0  # Если записей нет, возвращаем 0
        discount = total * 0.1  # Рассчитываем скидку
        final_total = total - discount
        return jsonify({"total": total, "discount": discount, "final_total": final_total})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})
    cursor.execute('''SELECT SUM(products.price) FROM purchases
                      JOIN products ON purchases.product_id = products.product_id
                      WHERE purchases.customer_id = ?''', (customer_id,))
    total = cursor.fetchone()[0]
    if total:
        discount = total * 0.10
        final_total = total - discount
        return jsonify({"total": total, "discount": discount, "final_total": final_total})
    return jsonify({"total": 0, "discount": 0, "final_total": 0})
    
    

def calculate_total(customer_id):
    try:
        # Найти сумму всех товаров с указанным customer_id
        cursor.execute("SELECT SUM(price) FROM products WHERE customer_id = ?", (customer_id,))
        total = cursor.fetchone()[0] or 0  # Если нет записей, возвращаем 0
        discount = total * 0.1  # Рассчитываем скидку
        final_total = total - discount
        return jsonify({"total": total, "discount": discount, "final_total": final_total})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route('/update_customer/<int:product_id>', methods=['POST'])
def update_customer(product_id):
    customer_id = request.form['customer_id']
    try:
        cursor.execute("UPDATE products SET customer_id = ? WHERE id = ?", (customer_id, product_id))
        conn.commit()  # Явно фиксируем транзакцию
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e))


    @app.route('/reset_ids', methods=['POST'])
    def reset_ids():
        try:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='products'")  # Сбросить автоинкремент
            conn.commit()
            return jsonify({"success": True, "message": "ID sequence reset successfully!"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})



# Example usage
if __name__ == "__main__":
    # Uncomment to import data from Excel
    # excel_file_path = 'Kirputori _ 30.11 .xlsx'  # File located in the same directory
    # import_excel_to_db(excel_file_path)

    app.run(debug=True)

# Commit changes and close connection
conn.commit()
