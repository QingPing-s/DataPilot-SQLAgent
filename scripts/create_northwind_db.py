from __future__ import annotations

import calendar
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path


DB_PATH = Path("data/northwind/northwind.db")
RANDOM_SEED = 20260624
ORDER_COUNT = 500

CUSTOMERS = [
    ("ALFKI", "Alfreds Futterkiste", "Maria Anders", "Germany", "Berlin"),
    ("ANATR", "Ana Trujillo Emparedados", "Ana Trujillo", "Mexico", "Mexico City"),
    ("AROUT", "Around the Horn", "Thomas Hardy", "UK", "London"),
    ("BERGS", "Berglunds snabbkop", "Christina Berglund", "Sweden", "Lulea"),
    ("BONAP", "Bon app", "Laurence Lebihan", "France", "Marseille"),
    ("CENTC", "Centro comercial Moctezuma", "Francisco Chang", "Mexico", "Mexico City"),
    ("ERNSH", "Ernst Handel", "Roland Mendel", "Austria", "Graz"),
    ("QUICK", "QUICK-Stop", "Horst Kloss", "Germany", "Cunewalde"),
    ("BLAUS", "Blauer See Delikatessen", "Hanna Moos", "Germany", "Mannheim"),
    ("EASTC", "Eastern Connection", "Ann Devon", "UK", "London"),
    ("FOLKO", "Folk och fa HB", "Maria Larsson", "Sweden", "Bracke"),
    ("HUNGC", "Hungry Coyote Import Store", "Yoshi Latimer", "USA", "Elgin"),
]

# Managers appear before employees that reference them so foreign keys remain valid during insertion.
EMPLOYEES = [
    (2, "Andrew", "Fuller", "Vice President, Sales", "USA", "2018-04-01", None),
    (5, "Steven", "Buchanan", "Sales Manager", "UK", "2019-10-17", 2),
    (1, "Nancy", "Davolio", "Sales Representative", "USA", "2020-05-01", 2),
    (3, "Janet", "Leverling", "Sales Representative", "USA", "2020-11-15", 2),
    (4, "Margaret", "Peacock", "Sales Representative", "USA", "2019-03-20", 2),
    (6, "Michael", "Suyama", "Sales Representative", "USA", "2021-08-15", 5),
    (7, "Robert", "King", "Sales Representative", "UK", "2020-01-02", 5),
    (8, "Laura", "Callahan", "Inside Sales Coordinator", "USA", "2022-05-10", 2),
]

SHIPPERS = [
    (1, "Speedy Express"),
    (2, "United Package"),
    (3, "Federal Shipping"),
]

SUPPLIERS = [
    (1, "Exotic Liquids", "UK"),
    (2, "New Orleans Cajun Delights", "USA"),
    (3, "Grandma Kelly's Homestead", "USA"),
    (4, "Tokyo Traders", "Japan"),
    (5, "Cooperativa de Quesos", "Spain"),
    (6, "Pavlova Ltd.", "Australia"),
]

CATEGORIES = [
    (1, "Beverages", "Soft drinks, coffees, teas, beers, and ales"),
    (2, "Condiments", "Sweet and savory sauces, relishes, spreads, and seasonings"),
    (3, "Confections", "Desserts, candies, and sweet breads"),
    (4, "Dairy Products", "Cheeses"),
    (5, "Grains/Cereals", "Breads, crackers, pasta, and cereal"),
    (6, "Meat/Poultry", "Prepared meats"),
    (7, "Produce", "Dried fruit and bean curd"),
    (8, "Seafood", "Seaweed and fish"),
]

# product_id, name, supplier_id, category_id, unit_price, unit_cost, reorder_level, discontinued
PRODUCTS = [
    (1, "Chai", 1, 1, 18.00, 10.20, 20, 0),
    (2, "Chang", 1, 1, 19.00, 11.40, 20, 0),
    (3, "Aniseed Syrup", 1, 2, 10.00, 5.10, 15, 0),
    (4, "Chef Anton's Cajun Seasoning", 2, 2, 22.00, 13.20, 10, 0),
    (5, "Chef Anton's Gumbo Mix", 2, 2, 21.35, 13.50, 15, 1),
    (6, "Grandma's Boysenberry Spread", 3, 2, 25.00, 14.20, 15, 0),
    (7, "Uncle Bob's Organic Dried Pears", 3, 7, 30.00, 18.60, 20, 0),
    (8, "Northwoods Cranberry Sauce", 3, 2, 40.00, 25.00, 10, 0),
    (9, "Mishi Kobe Niku", 4, 6, 97.00, 71.00, 10, 0),
    (10, "Ikura", 4, 8, 31.00, 20.10, 15, 0),
    (11, "Queso Cabrales", 5, 4, 21.00, 12.30, 20, 0),
    (12, "Queso Manchego La Pastora", 5, 4, 38.00, 23.50, 15, 0),
    (13, "Konbu", 4, 8, 6.00, 3.20, 20, 0),
    (14, "Tofu", 4, 7, 23.25, 13.80, 15, 0),
    (15, "Alice Mutton", 6, 6, 39.00, 25.40, 10, 1),
    (16, "Pavlova", 6, 3, 17.45, 9.90, 20, 0),
    (17, "Carnarvon Tigers", 6, 8, 62.50, 41.00, 10, 0),
    (18, "Teatime Chocolate Biscuits", 6, 3, 9.20, 4.80, 25, 0),
    (19, "Sir Rodney's Marmalade", 1, 3, 81.00, 52.00, 10, 0),
    (20, "Gustaf's Knackebrod", 3, 5, 21.00, 11.70, 20, 0),
]


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;

        CREATE TABLE customers (
            customer_id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            contact_name TEXT NOT NULL,
            country TEXT NOT NULL,
            city TEXT NOT NULL
        );

        CREATE TABLE employees (
            employee_id INTEGER PRIMARY KEY,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            title TEXT NOT NULL,
            country TEXT NOT NULL,
            hire_date TEXT NOT NULL,
            reports_to INTEGER,
            FOREIGN KEY(reports_to) REFERENCES employees(employee_id)
        );

        CREATE TABLE shippers (
            shipper_id INTEGER PRIMARY KEY,
            company_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE suppliers (
            supplier_id INTEGER PRIMARY KEY,
            company_name TEXT NOT NULL,
            country TEXT NOT NULL
        );

        CREATE TABLE categories (
            category_id INTEGER PRIMARY KEY,
            category_name TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL
        );

        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            supplier_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            unit_price REAL NOT NULL CHECK(unit_price >= 0),
            unit_cost REAL NOT NULL CHECK(unit_cost >= 0 AND unit_cost <= unit_price),
            units_in_stock INTEGER NOT NULL CHECK(units_in_stock >= 0),
            reorder_level INTEGER NOT NULL CHECK(reorder_level >= 0),
            units_on_order INTEGER NOT NULL CHECK(units_on_order >= 0),
            discontinued INTEGER NOT NULL DEFAULT 0 CHECK(discontinued IN (0, 1)),
            FOREIGN KEY(supplier_id) REFERENCES suppliers(supplier_id),
            FOREIGN KEY(category_id) REFERENCES categories(category_id)
        );

        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id TEXT NOT NULL,
            employee_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            required_date TEXT NOT NULL,
            shipped_date TEXT,
            ship_country TEXT NOT NULL,
            ship_city TEXT NOT NULL,
            shipper_id INTEGER NOT NULL,
            freight REAL NOT NULL CHECK(freight >= 0),
            order_status TEXT NOT NULL CHECK(order_status IN ('Delivered', 'Shipped', 'Cancelled')),
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id),
            FOREIGN KEY(shipper_id) REFERENCES shippers(shipper_id)
        );

        CREATE TABLE order_details (
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            unit_price REAL NOT NULL CHECK(unit_price >= 0),
            cost_price REAL NOT NULL CHECK(cost_price >= 0),
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            discount REAL NOT NULL DEFAULT 0 CHECK(discount >= 0 AND discount <= 1),
            PRIMARY KEY(order_id, product_id),
            FOREIGN KEY(order_id) REFERENCES orders(order_id),
            FOREIGN KEY(product_id) REFERENCES products(product_id)
        );

        CREATE TABLE employee_targets (
            employee_id INTEGER NOT NULL,
            target_year INTEGER NOT NULL CHECK(target_year BETWEEN 2000 AND 2100),
            target_month INTEGER NOT NULL CHECK(target_month BETWEEN 1 AND 12),
            sales_target REAL NOT NULL CHECK(sales_target > 0),
            PRIMARY KEY(employee_id, target_year, target_month),
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        );

        CREATE TABLE returns (
            return_id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            return_date TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity > 0),
            reason TEXT NOT NULL,
            FOREIGN KEY(order_id, product_id) REFERENCES order_details(order_id, product_id)
        );

        CREATE TABLE inventory_transactions (
            transaction_id INTEGER PRIMARY KEY,
            product_id INTEGER NOT NULL,
            transaction_date TEXT NOT NULL,
            transaction_type TEXT NOT NULL CHECK(transaction_type IN ('Purchase', 'Sale', 'Return', 'Adjustment')),
            quantity INTEGER NOT NULL CHECK(quantity != 0),
            reference_order_id INTEGER,
            FOREIGN KEY(product_id) REFERENCES products(product_id),
            FOREIGN KEY(reference_order_id) REFERENCES orders(order_id)
        );

        CREATE INDEX idx_products_supplier ON products(supplier_id);
        CREATE INDEX idx_products_category ON products(category_id);
        CREATE INDEX idx_orders_customer ON orders(customer_id);
        CREATE INDEX idx_orders_employee ON orders(employee_id);
        CREATE INDEX idx_orders_shipper ON orders(shipper_id);
        CREATE INDEX idx_orders_order_date ON orders(order_date);
        CREATE INDEX idx_orders_status ON orders(order_status);
        CREATE INDEX idx_order_details_product ON order_details(product_id);
        CREATE INDEX idx_returns_order_product ON returns(order_id, product_id);
        CREATE INDEX idx_inventory_product_date ON inventory_transactions(product_id, transaction_date);
        CREATE INDEX idx_targets_period ON employee_targets(target_year, target_month);
        """
    )


def insert_seed_data(conn: sqlite3.Connection) -> None:
    rng = random.Random(RANDOM_SEED)
    conn.executemany("INSERT INTO customers VALUES (?, ?, ?, ?, ?)", CUSTOMERS)
    conn.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?, ?, ?)", EMPLOYEES)
    conn.executemany("INSERT INTO shippers VALUES (?, ?)", SHIPPERS)
    conn.executemany("INSERT INTO suppliers VALUES (?, ?, ?)", SUPPLIERS)
    conn.executemany("INSERT INTO categories VALUES (?, ?, ?)", CATEGORIES)
    conn.executemany(
        "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(*product[:6], 400, product[6], 0, product[7]) for product in PRODUCTS],
    )

    orders, order_details, returns = _generate_orders(rng)
    conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", orders)
    conn.executemany("INSERT INTO order_details VALUES (?, ?, ?, ?, ?, ?)", order_details)
    conn.executemany("INSERT INTO returns VALUES (?, ?, ?, ?, ?, ?)", returns)
    conn.executemany("INSERT INTO employee_targets VALUES (?, ?, ?, ?)", _generate_employee_targets(rng))

    transactions, final_stock = _generate_inventory_transactions(rng, orders, order_details, returns)
    conn.executemany("INSERT INTO inventory_transactions VALUES (?, ?, ?, ?, ?, ?)", transactions)
    replenishment_ids = {
        product_id
        for product_id, _ in sorted(final_stock.items(), key=lambda item: item[1])[:4]
    }
    for product_id, units_in_stock in final_stock.items():
        reorder_level = next(product[6] for product in PRODUCTS if product[0] == product_id)
        units_on_order = 100 if product_id in replenishment_ids or units_in_stock <= reorder_level else 0
        conn.execute(
            "UPDATE products SET units_in_stock = ?, units_on_order = ? WHERE product_id = ?",
            (units_in_stock, units_on_order, product_id),
        )


def _generate_orders(rng: random.Random):
    product_by_id = {product[0]: product for product in PRODUCTS}
    customer_weights = [15, 8, 11, 13, 9, 7, 16, 12, 5, 4, 3, 2]
    employee_ids = [1, 2, 3, 4, 5, 6, 7, 8]
    employee_weights = [22, 8, 18, 16, 10, 12, 9, 5]
    shipper_weights = [49, 33, 18]
    order_dates = sorted(_random_order_date(rng) for _ in range(ORDER_COUNT))
    orders = []
    order_details = []
    returns = []

    for index, order_date in enumerate(order_dates):
        order_id = 10001 + index
        customer = rng.choices(CUSTOMERS, weights=customer_weights, k=1)[0]
        employee_id = rng.choices(employee_ids, weights=employee_weights, k=1)[0]
        shipper_id = rng.choices([1, 2, 3], weights=shipper_weights, k=1)[0]
        product_count = rng.choices([2, 3, 4, 5, 6], weights=[8, 24, 35, 23, 10], k=1)[0]
        product_ids = rng.sample(list(product_by_id), product_count)
        cancelled = rng.random() < 0.045
        required_date = order_date + timedelta(days=rng.randint(7, 13))
        shipped_date = None if cancelled else order_date + timedelta(days=rng.randint(1, 17))
        order_status = "Cancelled" if cancelled else "Delivered"
        total_quantity = 0
        current_details = []

        for product_id in product_ids:
            product = product_by_id[product_id]
            inflation = 1 + 0.03 * (order_date.year - 2023)
            unit_price = round(product[4] * inflation, 2)
            cost_price = round(product[5] * inflation, 2)
            quantity = rng.randint(2, 28)
            discount = rng.choices([0.0, 0.05, 0.10, 0.15], weights=[54, 24, 16, 6], k=1)[0]
            detail = (order_id, product_id, unit_price, cost_price, quantity, discount)
            current_details.append(detail)
            order_details.append(detail)
            total_quantity += quantity

        freight = round(rng.uniform(8, 28) + total_quantity * rng.uniform(0.45, 1.15), 2)
        orders.append(
            (
                order_id,
                customer[0],
                employee_id,
                order_date.isoformat(),
                required_date.isoformat(),
                shipped_date.isoformat() if shipped_date else None,
                customer[3],
                customer[4],
                shipper_id,
                freight,
                order_status,
            )
        )

        if not cancelled and rng.random() < 0.10:
            returned_detail = rng.choice(current_details)
            return_date = shipped_date + timedelta(days=rng.randint(2, 24))
            return_quantity = rng.randint(1, min(4, returned_detail[4]))
            returns.append(
                (
                    20001 + len(returns),
                    order_id,
                    returned_detail[1],
                    return_date.isoformat(),
                    return_quantity,
                    rng.choice(["Damaged", "Wrong item", "Quality issue", "Customer changed mind"]),
                )
            )

    return orders, order_details, returns


def _random_order_date(rng: random.Random) -> date:
    year = rng.choices([2023, 2024, 2025], weights=[25, 33, 42], k=1)[0]
    month = rng.choices(
        list(range(1, 13)),
        weights=[7, 7, 8, 8, 9, 9, 10, 10, 11, 12, 15, 18],
        k=1,
    )[0]
    day = rng.randint(1, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _generate_employee_targets(rng: random.Random):
    target_base = {1: 7200, 2: 5600, 3: 6800, 4: 6500, 5: 5900, 6: 6200, 7: 5700, 8: 4300}
    targets = []
    for year in (2023, 2024, 2025):
        for month in range(1, 13):
            seasonality = 1.25 if month in (11, 12) else 1.10 if month in (8, 9, 10) else 1.0
            growth = 1 + 0.04 * (year - 2023)
            for employee_id in target_base:
                target = round(target_base[employee_id] * seasonality * growth * rng.uniform(0.94, 1.06), 2)
                targets.append((employee_id, year, month, target))
    return targets


def _generate_inventory_transactions(rng, orders, order_details, returns):
    order_lookup = {row[0]: row for row in orders}
    reorder_lookup = {product[0]: product[6] for product in PRODUCTS}
    balances = {product[0]: 400 for product in PRODUCTS}
    events = []
    for detail in order_details:
        order = order_lookup[detail[0]]
        if order[-1] != "Cancelled":
            events.append((order[3], 0, "Sale", detail[1], -detail[4], detail[0]))
    for returned in returns:
        events.append((returned[3], 1, "Return", returned[2], returned[4], returned[1]))
    events.sort()

    transactions = []
    transaction_id = 30001
    for product_id in balances:
        transactions.append((transaction_id, product_id, "2023-01-01", "Adjustment", 400, None))
        transaction_id += 1

    for event_date, _, event_type, product_id, quantity, order_id in events:
        if event_type == "Sale" and balances[product_id] + quantity < reorder_lookup[product_id]:
            purchase_quantity = rng.randint(180, 280)
            transactions.append((transaction_id, product_id, event_date, "Purchase", purchase_quantity, None))
            balances[product_id] += purchase_quantity
            transaction_id += 1
        transactions.append((transaction_id, product_id, event_date, event_type, quantity, order_id))
        balances[product_id] += quantity
        transaction_id += 1

    return transactions, balances


def count_rows(conn: sqlite3.Connection) -> dict[str, int]:
    tables = [
        "customers",
        "employees",
        "shippers",
        "suppliers",
        "categories",
        "products",
        "orders",
        "order_details",
        "employee_targets",
        "returns",
        "inventory_transactions",
    ]
    return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}


def create_northwind_db(db_path: Path = DB_PATH) -> Path:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        create_schema(conn)
        insert_seed_data(conn)
        conn.commit()

    return db_path


def main() -> None:
    db_path = create_northwind_db()
    with sqlite3.connect(db_path) as conn:
        row_counts = count_rows(conn)

    print(f"Database path: {db_path.resolve()}")
    print("Table row counts:")
    for table, count in row_counts.items():
        print(f"- {table}: {count}")
    print("Northwind demo database created successfully.")


if __name__ == "__main__":
    main()
