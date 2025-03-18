# ToDoList

### About
TaskMaster Bot is a Telegram-based task management solution that helps users organize deadlines, set reminders, and track tasks via a built-in MiniApp frontend. 


### Tech Stack
* Telegram Bot API & MiniApp (User interaction and frontend)

* Flask (Backend server and API routes)

* Celery (Asynchronous task scheduling for reminders and deadlines)

* Redis (Message broker for Celery and real-time notifications)

* MongoDB (Database for tasks, users, and reminders)

* Docker & Docker-compose (Containerization and deployment)

### Installation
**Clone the repository:**

```bash
git clone https://github.com/MRuslanR/ToDoList.git
```

```bash
cd ToDoList
```
**Ensure Docker is installed and running.
Build and start the containers:**

```bash
docker-compose build  
docker-compose up 
```

**Set environment variables for MongoDB, Telegram API tokens, and Redis in the .env file.**

