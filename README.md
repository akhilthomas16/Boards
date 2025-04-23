# Boards
Web Forum using Django

## Features
- User registration and authentication
- Create, edit, and delete boards
- Create, edit, and delete topics within boards
- Post and reply to messages in topics
- User profiles with avatars
- Markdown support for posts
- Search functionality

## Technologies
- Python 3.x
- Django 4.x
- Bootstrap 5
- PostgreSQL

## Installation
1. Clone the repository
```bash
git clone https://github.com/yourusername/boards.git
cd boards
```

2. Create virtual environment and install dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

3. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your settings
```

4. Run migrations
```bash
python manage.py migrate
```

5. Start development server
```bash
python manage.py runserver
```

## License
MIT License