# 日常小店 · 简化版

一个基于 Flask + SQLite 的简易商城，支持注册登录、商品搜索、购物车和订单查看。

## 运行

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

打开 http://127.0.0.1:5000，注册账号后选购。没有默认账号。下单只生成订单，不接入支付、库存或配送。

数据库首次运行时自动创建，重启保留数据。金额使用整数分；下单时保存商品名称、单价和数量，并在同一事务中清空购物车。商品页加入购物车会将该商品数量设为 1，购物车内可修改为 0–99，0 表示移除。

## 文件

- `app.py`：应用、认证、购物车和订单路由。
- `schema.sql`：五张表与四件示例商品。
- `templates/`、`static/style.css`：中文页面与响应式样式，无前端构建步骤。
- `test_app.py`：自动化测试。

运行测试：

```sh
.venv/bin/python -m unittest -v
```

可选环境变量：`SHOP_DB_PATH` 指定 SQLite 路径（默认 `data/shop.db`）；`SHOP_SECRET_KEY` 指定会话密钥（不设置时每次启动随机生成，旧登录会失效）。默认仅监听本机 5000 端口。
