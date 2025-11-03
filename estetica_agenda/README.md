# estetica_agenda — Protótipo Django de Agendamento (UNIVESP PI2)

Este é o projeto pronto para rodar localmente e fazer deploy no Render.
**Observação**: o arquivo `db.sqlite3` inclui apenas os dados da app (profissional, serviços e um booking de demonstração).
Ele NÃO contém tabelas do auth do Django (por limitação do ambiente aqui). Por isso, crie o superuser localmente seguindo as instruções abaixo.

## Como rodar localmente (no seu computador)
1. Clone este projeto ou extraia o .zip.
2. Crie e ative um virtualenv com Python 3.11+.
3. Instale dependências:
```bash
pip install -r requirements.txt
```
4. Crie as migrations e aplique (recomendado; esta base já contém os dados de app):
```bash
python manage.py makemigrations
python manage.py migrate
```
5. Crie um superuser (por segurança, digite credenciais desejadas):
```bash
python manage.py createsuperuser
```
6. (Opcional) Se quiser sobrescrever a demo de app e usar o DB fornecido, pule migrations de criação de auth, mas é mais seguro migrar e criar superuser.
7. Rode o servidor:
```bash
python manage.py runserver
```
Acesse http://127.0.0.1:8000/

## Notas importantes
- Endpoint `/notify-whatsapp/` é simulado e apenas grava no log do servidor.
- Para deploy no Render: configure `SECRET_KEY`, `DEBUG=False` e `ALLOWED_HOSTS`, e adicione `DATABASE_URL` se quiser usar Postgres.
- O banco `db.sqlite3` contém tabelas da app para demonstrar serviços e bookings.
