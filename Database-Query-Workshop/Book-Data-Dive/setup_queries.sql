-- Creating the books table
CREATE TABLE books (
    book_id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    publication_year INT NOT NULL,
    isbn VARCHAR(13) NOT NULL
);

-- Creating the users table
CREATE TABLE users (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    registration_date DATE NOT NULL
);

-- Creating the borrowed_books table
CREATE TABLE borrowed_books (
    borrow_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    book_id INT,
    borrow_date DATE NOT NULL,
    return_date DATE,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (book_id) REFERENCES books(book_id)
);

-- Inserting data into books table
INSERT INTO books (title, author, publication_year, isbn) VALUES
('Harry Potter and the Sorcerer''s Stone', 'J.K. Rowling', 1997, '9780747532699'),
('The Hobbit', 'J.R.R. Tolkien', 1937, '9780547928227'),
('To Kill a Mockingbird', 'Harper Lee', 1960, '9780061120084'),
('1984', 'George Orwell', 1949, '9780451524935');

-- Inserting data into users table
INSERT INTO users (first_name, last_name, email, registration_date) VALUES
('John', 'Doe', 'john.doe@email.com', '2022-01-15'),
('Jane', 'Smith', 'jane.smith@email.com', '2022-02-20'),
('Alice', 'Johnson', 'alice.johnson@email.com', '2022-03-10');

-- Inserting data into borrowed_books table
INSERT INTO borrowed_books (user_id, book_id, borrow_date, return_date) VALUES
(1, 1, '2022-04-01', NULL),
(2, 2, '2022-04-05', '2022-04-20'),
(3, 3, '2022-04-10', NULL);
