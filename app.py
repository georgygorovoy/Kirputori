import sqlite3
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Подключение к базе данных
conn = sqlite3.connect("store.db", check_same_thread=False)
cursor = conn.cursor()

# Маршруты приложения
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
    price = float(request.form['price'])
    product_id = request.form['product_id']

    try:
        # Найти максимальный текущий ID
        cursor.execute('SELECT MAX(id) FROM products')
        max_id = cursor.fetchone()[0] or 0  # Если таблица пуста, начать с 0
        new_id = max_id + 1

        # Добавить продукт с вручную рассчитанным ID
        cursor.execute('''INSERT INTO products (id, name, price, product_id) VALUES (?, ?, ?, ?)''',
                       (new_id, name, float(price), product_id))
        cursor.execute("INSERT INTO products (name, price, product_id) VALUES (?, ?, ?)", (name, price, product_id))
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
    cursor.execute('''SELECT SUM(products.price) FROM purchases
                      JOIN products ON purchases.product_id = products.product_id
                      WHERE purchases.customer_id = ?''', (customer_id,))
    total = cursor.fetchone()[0]
    if total:
        discount = total * 0.10
        final_total = total - discount
        return jsonify({"total": total, "discount": discount, "final_total": final_total})
    return jsonify({"total": 0, "discount": 0, "final_total": 0})
    
    


@app.route('/update_customer/<int:product_id>', methods=['POST'])
def update_customer(product_id):
    customer_id = request.form['customer_id']
    try:
        cursor.execute("UPDATE products SET customer_id = ? WHERE id = ?", (customer_id, product_id))
        conn.commit()
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


@app.route('/calculate_total/<string:customer_id>', methods=['GET'])
def calculate_total(customer_id):
    try:
        # Найти сумму цен всех товаров с указанным customer_id
        cursor.execute("SELECT SUM(price), COUNT(*) FROM products WHERE customer_id = ?", (customer_id,))
        result = cursor.fetchone()
        total = result[0] or 0
        item_count = result[1]

        # Рассчитать скидку в зависимости от количества товаров
        if item_count >= 2:
            discount = min(item_count * 2, 30)  # Удвоенная скидка за каждый товар начиная с двух, максимум 30%
        else:
            discount = 0

        discount_amount = total * (discount / 100)
        final_total = total - discount_amount

        return jsonify({
            "total": total,
            "discount": f"{discount}%",
            "final_total": final_total
        })
    except Exception as e:
        return jsonify(success=False, error=str(e))


if __name__ == "__main__":
    app.run(debug=True)
