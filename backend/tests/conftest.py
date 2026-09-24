import os

# app.database 在导入时按 settings.database_url 建引擎；
# API 测例用 SQLite 内存库 + 依赖覆盖，无需真实 Postgres/psycopg2。
# 必须在任何 app.* 模块被导入之前设置。
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/hangrail_pytest.db")
