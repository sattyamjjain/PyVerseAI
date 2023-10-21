-- Retrieve the Top 10 Most Borrowed Books

SELECT b.title, COUNT(bb.borrow_id) AS borrow_count
FROM books b
JOIN borrowed_books bb ON b.book_id = bb.book_id
GROUP BY b.title
ORDER BY borrow_count DESC
LIMIT 10;

-- Stored Procedure for Average Borrow Duration

DELIMITER //
CREATE PROCEDURE AverageBorrowDuration(IN given_book_id INT)
BEGIN
    SELECT AVG(DATEDIFF(return_date, borrow_date)) AS avg_duration
    FROM borrowed_books
    WHERE book_id = given_book_id AND return_date IS NOT NULL;
END //
DELIMITER ;

-- Find the User Who Has Borrowed the Most Books

SELECT u.first_name, u.last_name, COUNT(bb.borrow_id) AS total_borrows
FROM users u
JOIN borrowed_books bb ON u.user_id = bb.user_id
GROUP BY u.user_id, u.first_name, u.last_name
ORDER BY total_borrows DESC
LIMIT 1;

-- Create an Index on the publication_year Column

CREATE INDEX idx_publication_year ON books(publication_year);

-- Find Books Published in 2020 Not Borrowed by Any User

SELECT b.book_id, b.title, b.author
FROM books b
LEFT JOIN borrowed_books bb ON b.book_id = bb.book_id
WHERE b.publication_year = 2020 AND bb.borrow_id IS NULL;

-- List Users Who Have Borrowed Books Published by a Specific Author

SELECT DISTINCT u.first_name, u.last_name
FROM users u
JOIN borrowed_books bb ON u.user_id = bb.user_id
JOIN books b ON bb.book_id = b.book_id
WHERE b.author = 'J.K. Rowling';

-- Create a Trigger to Update return_date

DELIMITER //
CREATE TRIGGER update_return_date
BEFORE UPDATE ON borrowed_books
FOR EACH ROW
BEGIN
    IF NEW.return_date IS NULL THEN
        SET NEW.return_date = CURDATE();
    END IF;
END //
DELIMITER ;
