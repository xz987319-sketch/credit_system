# 银行信贷申请流程模拟系统

基于 **Python 3.11+**、**Django 5.2**、**SQLite** 的毕业设计演示项目，包含 H5 进件、员工端、审核员端、超级管理员信审与 Django Admin（django-unfold）。

## 环境要求

- Python 3.11 或以上  
- 建议使用虚拟环境

## 安装依赖

在项目根目录（含 `manage.py`）执行：

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 数据库迁移

首次部署或清空数据库后执行：

```bash
python manage.py makemigrations apply
python manage.py migrate
```

迁移完成后会在项目根目录生成 `db.sqlite3`。

## 演示数据（可选）

创建演示银行 `0000`、**四类卡产品**（普卡 / 金卡 / 白金卡 / 钻石卡及对应额度区间）、普通员工 `staff` 与审核员 `auditor`（密码均为 `demo123`）：

```bash
python manage.py seed_demo
```

卡种与额度区间可在 `apply/management/commands/seed_demo.py` 中的 `CARD_SPECS` 修改后重新执行该命令同步到数据库。

### 申请金额输入（H5 / 补充资料）

- **模板**：`apply/templates/apply_h5.html`、`return_edit.html` 对「申请金额」字段附带区间说明与实时反馈；`base.html` 已全局引入 `static/js/apply_amount_input.js`（仅当表单存在 `name="amount"` 时生效）。
- **控件**：`apply/widgets.py` 中 `CardProductLimitsSelect` 为每个卡种 `<option>` 输出 `data-credit-min` / `data-credit-max`。
- **后端**：`apply/utils/amount_validate.py` 的 `validate_submitted_amount_string` 在 `H5ApplyForm.clean_amount`、`ReturnEditForm.clean_amount` 中调用，防止绕过前端。
- **独立演示页**（纯 HTML，可直接用浏览器打开文件）：`static/demo_credit_amount_standalone.html`。

## 创建超级管理员

用于登录 `/admin/` 与前台「待信审」菜单（需 `is_superuser=True`）：

```bash
python manage.py createsuperuser
```

按提示输入用户名、邮箱与密码。超级管理员的「所属银行」可在 Admin 中留空。

## 运行开发服务器

本项目统一使用 **8080** 端口（避免与本机已占用 **8000** 端口的其他项目冲突）。`apply` 应用已覆盖默认 `runserver` 命令，不写端口时即为 8080：

```bash
python manage.py runserver
```

也可显式指定（与其他参数组合时更清晰）：

```bash
python manage.py runserver 8080
```

常用入口：

| 说明 | 地址 |
|------|------|
| H5 申请（无需登录） | http://127.0.0.1:8080/apply/ |
| 员工登录 | http://127.0.0.1:8080/login/ |
| 业务首页（登录后） | http://127.0.0.1:8080/ |
| Django Admin | http://127.0.0.1:8080/admin/ |

### 演示登录说明

- **普通员工**：银行号 `0000`，用户名 `staff`，密码 `demo123`（需先执行 `seed_demo`）。  
- **审核员**：银行号 `0000`，用户名 `auditor`，密码 `demo123`。  
- **超级管理员**：使用 `createsuperuser` 创建的账号登录 `/admin/`；前台信审菜单需该账号且 `is_superuser` 为真。

登录页验证码为明文展示，输入时需与页面显示一致（不区分大小写）。

## 项目结构摘要

- `credit_apply/`：Django 项目配置（`settings.py`、`urls.py`）。  
- `apply/`：业务应用（模型、视图、表单、路由、模板、自定义认证）。  
- `static/`：自定义 CSS 等静态资源。

## 常见问题

- **迁移顺序错误**：若曾混用其他 `settings` 或旧数据库，可删除根目录 `db.sqlite3` 与 `apply/migrations/` 下除 `__init__.py` 外的迁移文件后，重新执行 `makemigrations` 与 `migrate`（仅适用于可清空数据的开发环境）。  
- **用户名全局唯一警告**：自定义用户按「银行 + 用户名」联合唯一，Django 可能提示 `USERNAME_FIELD` 非全局唯一，属预期行为；员工登录请始终使用「银行号 + 用户名 + 密码」。
