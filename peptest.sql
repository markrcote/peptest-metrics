CREATE TABLE branch (
    id INT AUTO_INCREMENT,
    PRIMARY KEY (id),
    name VARCHAR(255) COLLATE utf8_bin
);

CREATE TABLE platform (
    id INT AUTO_INCREMENT,
    PRIMARY KEY (id),
    name VARCHAR(255) COLLATE utf8_bin
);

CREATE TABLE test (
    id INT AUTO_INCREMENT,
    PRIMARY KEY (id),
    name VARCHAR(255) COLLATE utf8_bin
);

CREATE TABLE result (
    id INT AUTO_INCREMENT,
    PRIMARY KEY (id),
    branch_id INT,
    FOREIGN KEY (branch_id) REFERENCES branch(id),
    platform_id INT,
    FOREIGN KEY (platform_id) REFERENCES platform(id),
    test_id INT,
    FOREIGN KEY (test_id) REFERENCES test(id),
    run INT,
    action VARCHAR(256) COLLATE utf8_bin,
    builddate DATETIME,
    revision VARCHAR(12) COLLATE utf8_bin,
    unresponsive_period INT DEFAULT 0
);
