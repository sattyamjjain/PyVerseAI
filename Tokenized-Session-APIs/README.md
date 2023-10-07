# Tokenized-Session-APIs

---

### **Description**:
`Tokenized-Session-APIs` is a backend system designed to manage and facilitate session bookings between students and deans in a university context. Through a series of API endpoints, students can view available dean slots, make bookings, and deans can monitor their pending sessions.

---

### **Table of Contents**:
- [Features](#features)
- [Requirements](#requirements)
- [Setup & Installation](#setup-&-installation)
- [Database Structure](#database-structure)
- [Authentication](#authentication)
- [Contribution](#contribution)

---

### **Features**:

- **User Authentication**: Secure login system for students and deans. Upon successful login, users receive a unique token for authentication in subsequent API calls.
  
- **Session Viewing**: Students can view available dean session slots. Deans can view their pending sessions with students.
  
- **Session Booking**: Students can book available slots with deans.
  
- **Token-based Security**: All API interactions, post-login, require a valid bearer token for access.

---

### **Requirements**:
- Python 3.7+
- MongoDB (or the specific database used for this project)
- Dependencies listed in `requirements.txt`

---

### **Setup & Installation**:

1. **Clone the Repository**:
   ```bash
   git clone [repository-link]
   cd Tokenized-Session-APIs
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**:
   ```bash
   python main.py
   ```

---


### **Database Structure**:
The application uses MongoDB to manage user data, session bookings, and available slots. For a detailed understanding of the database schema and relationships, please refer to the `db` directory.

---

### **Authentication**:
The system uses bearer token authentication to secure API endpoints. Tokens are issued upon successful login and must be provided in the header of subsequent API requests to ensure authorized access.

---

### **Contribution**:
Contributions to `Tokenized-Session-APIs` are welcome! Whether it's feature enhancements, bug fixes, or documentation improvements, your inputs are valued.

---