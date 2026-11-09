# CampusShare 🎓

### A Student-to-Student Campus Resource Sharing Platform

CampusShare is a web-based platform designed to help college students share, discover, and manage useful resources within their campus community.

Students can list items they want to rent, explore resources shared by other students, submit booking requests, and manage room-sharing listings. The platform aims to make campus resource sharing easier, more organized, and accessible.

---

## 🚀 Features

### 1. Student Authentication
- Student registration using college student ID.
- Email verification through a one-time password (OTP).
- Secure password hashing.
- Student login and logout.
- Forgot-password functionality with email OTP verification.

### 2. Student Dashboard
- Personalized dashboard for logged-in students.
- Overview of personal resource listings.
- Booking activity summary.
- Pending booking request count.
- Recent booking activity.

### 3. Resource Management
- Add resources with titles and descriptions.
- Select resource categories and conditions.
- Set rental prices.
- Upload resource images.
- Browse resources shared by other students.
- View resource details.
- Delete your own resource listings, subject to booking-history restrictions.

### 4. Booking Management
- Submit booking requests for available resources.
- Select rental start and end dates.
- Automatically calculate rental costs.
- View personal booking history.
- Receive booking requests from other students.
- Accept or reject pending booking requests.
- Prevent overlapping accepted bookings.

### 5. Room Sharing
- Publish room or vacant-bed listings.
- Specify room type, location, rent, and available beds.
- Set gender preferences and facilities.
- Select room availability dates.
- Upload multiple room images.
- View and manage personal room listings.
- Delete your own room listings.

### 6. User Interface
- Responsive web interface.
- HTML templates using Jinja.
- Custom CSS styling.
- JavaScript-based form interactions.
- Flash messages for application feedback.

---

## 🛠️ Technologies Used

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web application framework |
| SQLite | Database |
| HTML5 | Page structure |
| CSS3 | Styling and layout |
| JavaScript | Frontend interactions |
| Jinja2 | Dynamic HTML templates |
| Werkzeug | Password hashing and file utilities |

---

## 📂 Project Structure

```text
CampusShare/
│
├── app.py
├── database.py
├── init_db.py
├── schema.sql
├── config.py
├── requirements.txt
├── .env
│
├── routes/
│   └── auth.py
│
├── services/
│   └── email_service.py
│
├── templates/
│   ├── base.html
│   ├── home.html
│   ├── dashboard.html
│   ├── login.html
│   ├── register.html
│   ├── add_resource.html
│   ├── resources.html
│   ├── resource_details.html
│   ├── post_room.html
│   ├── my_room_listings.html
│   ├── my_bookings.html
│   ├── booking_requests.html
│   └── ...
│
└── static/
    ├── css/
    │   └── style.css
    │
    ├── js/
    │
    └── uploads/
```

---

## ⚙️ Installation and Setup

Follow these steps to run CampusShare locally.

### Prerequisites

- Python 3.x
- pip (Python package installer)
- A code editor such as Visual Studio Code

### Step 1: Clone or download the project

Open your terminal and navigate to the project directory.

### Step 2: Create a virtual environment

```bash
python -m venv venv
```

Activate it:

**Windows:**
```bash
venv\Scripts\activate
```

**Linux / macOS:**
```bash
source venv/bin/activate
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure environment variables

Configure the required email settings and application secrets in your local `.env` file, using the variable names expected by your project's configuration and email service.

Do not upload real credentials, passwords, or secret keys to GitHub.

### Step 5: Initialize the database

```bash
python init_db.py
```

This initializes the SQLite database using the project's database schema.

### Step 6: Run the Flask application

```bash
flask run
```

### Step 7: Open CampusShare

Visit:

```text
http://127.0.0.1:5000
```

Register a student account and explore the application.

---

## 🗄️ Database

CampusShare uses SQLite for storing application data.

The database manages information related to:

- Students
- Registration OTPs
- Password reset records
- Resource listings
- Booking requests
- Payments
- Room listings
- Room images

The database connection and SQL operations are managed through `database.py`.

---

## 🔐 Security and Validation

The application includes:

- Password hashing.
- Email OTP verification.
- OTP expiration and attempt limits.
- Session-based authentication.
- Ownership checks for resource and room-listing deletion.
- Server-side form validation.
- File type and upload-size validation.
- Protection of booking history when deleting resources.

---

## 🎯 Project Objective

The main objective of CampusShare is to encourage resource sharing among college students.

Instead of purchasing every item individually, students can discover and rent resources from other students. The room-sharing feature also helps students find and share accommodation opportunities within their campus community.

---

## 🎓 CS50x Final Project

**Project Name:** CampusShare
**Course:** CS50x – Introduction to Computer Science
**Project Type:** Web Application
**Backend:** Python and Flask
**Database:** SQLite

### Demonstration Video

[Add your CS50 project demonstration video link here.]

### AI Assistance Disclosure

ChatGPT was used as a learning and development assistant during parts of the project, including programming explanations, debugging guidance, and implementation suggestions. The project code and final implementation were reviewed and tested by the student.

---

## 👨‍💻 Conclusion

CampusShare brings students together through a shared digital platform where they can list, discover, rent, and manage campus resources and accommodation opportunities.

**Share resources. Save money. Build a stronger campus community.**
