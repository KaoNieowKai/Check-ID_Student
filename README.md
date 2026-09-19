# 🏫✨ Student Activity Attendance System ✨🏫

Welcome to the **Student Activity Attendance System**! 💖 This application is beautifully designed to help teachers and schools manage student attendance for various activities, workshops, and events with ease. Say goodbye to manual roll calls and hello to smart QR code check-ins! 📱✨

---

## 🏗️ 💻 System Architecture & Technology Stack

Our system is built with a modern, fast, and reliable architecture:

### ⚙️ Backend (The Magic Behind the Scenes)
* **Framework**: FastAPI (Python) ⚡ Super fast!
* **Server**: Uvicorn 🦄
* **Database ORM**: SQLAlchemy 📚
* **Database Engine**: SQLite (or any SQL-compatible DB) 🗄️
* **Real-time Magic**: WebSockets (Watch attendance update live!) 🔄
* **Authentication**: JWT (JSON Web Tokens) + Passlib/Bcrypt 🔒 Super secure!
* **Templating**: Jinja2 🎨

### 🌐 Frontend (What You See)
* **Core**: HTML5, CSS3, Vanilla JavaScript 🖥️
* **Dynamic Content**: Jinja2 templates 🌟

---

## 🗂️ 🧑‍🎓 Core Data Models

Here are the key parts that make our system work:

* 👩‍🏫 **User**: Staff accounts for our lovely Admins and Teachers.
* 🎒 **Student**: Student information (ID, Name, Grade, Room).
* 🎈 **Activity**: Big events like "Sports Day" or "Science Fair".
* 📅 **ActivitySession**: Specific time slots for the activities.
* ✅ **AttendanceRecord**: The proof that a student was there!
* 🎫 **QRToken**: Short-lived, secure tokens for dynamic QR codes.
* ⏳ **CheckinSession**: A safe waiting room while students confirm their check-in.
* 📝 **AuditLog**: Keeps track of actions to keep everything transparent.

---

## 🚀 🎯 Application Workflows

### 1️⃣ 👑 Administrator Workflow
* **Authentication**: Secure login using credentials. 🔐
* **User Management**: Create and manage teacher accounts with love. 👥
* **System Monitoring**: View audit logs to keep the system safe. 🔍

### 2️⃣ 👩‍🏫 Teacher Workflow
* **Dashboard Access**: Get a beautiful overview of all activities. 📊
* **Activity Management**: Create and schedule fun sessions. 📆
* **Attendance Monitoring**: 
  * 📸 Show an auto-refreshing, dynamic QR code to the class.
  * 👀 Watch students check in *live* via WebSockets!
  * ✍️ Manually check in students who need a little help.
* **Reporting**: Export reports to see how many joined the fun. 📈

### 3️⃣ 📱 Student Check-in Workflow
Super quick and easy—no account needed!

1. **Scan 📸**: Scan the beautiful QR code displayed by the teacher.
2. **Session Initiation ⏳**: The system securely validates the code.
3. **Identification 🆔**: Pick your grade and enter your Student ID.
4. **Verification ✅**: See your name and make sure it's you!
5. **Confirmation 🎉**: Tap confirm, and you're all set!

---

## 🛡️ 🔒 Security and Privacy Concepts

We care deeply about privacy and keeping data safe:

* **Environment Configuration 🌍**: Secrets (like database URLs) are kept hidden in a `.env` file. We never share our secrets! 🤫
* **Authentication Security 🔑**: Passwords are securely hashed using `bcrypt`, and we use JWT for safe travels across the app.
* **QR Code Security 🔄**: Our QR codes expire super fast (e.g., in 30 seconds). This means no taking photos to share with friends at home! 🚫📸
* **Data Privacy 🕵️‍♀️**: Student data is kept safe and is only accessible by authorized teachers and admins.

---

## 🛠️ 👩‍💻 Development Notes

### ⚙️ Configuration Setup
We use environment variables for our settings. For example:
* `DATABASE_URL`: Where our database lives.
* `SECRET_KEY`: The magic key for JWTs.
* `ACCESS_TOKEN_EXPIRE_MINUTES`: How long the magic lasts.

*(Note: Keep these a secret! Never upload them to version control. 🤫)*

### 🚀 Running the Application
Ready to start? Run this command:
```bash
# Start the server with Uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---
*Built with ❤️ for the best check-in experience!*  
*created by **RyzerX (Tanakrit Phumcharoen)** from Nakprasith 79*
