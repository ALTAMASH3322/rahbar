-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Jan 27, 2025 at 02:58 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `rahbar`
--

-- --------------------------------------------------------

--
-- Table structure for table `approval`
--

CREATE TABLE `approval` (
  `approval_id` int(11) NOT NULL,
  `payment_id` int(11) NOT NULL,
  `approver_id` int(11) NOT NULL,
  `status` enum('Pending','Approved','Rejected') DEFAULT 'Pending',
  `comments` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `bank_details`
--

CREATE TABLE `bank_details` (
  `bank_detail_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `bank_name` varchar(255) NOT NULL,
  `account_number` varchar(20) NOT NULL,
  `ifsc_code` varchar(11) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `bank_details`
--

INSERT INTO `bank_details` (`bank_detail_id`, `user_id`, `bank_name`, `account_number`, `ifsc_code`, `created_at`, `updated_at`) VALUES
(1, 7, 'State Bank of India', '123456789012', 'SBIN0001234', '2025-01-25 18:48:22', '2025-01-25 18:48:22'),
(2, 8, 'HDFC Bank', '987654321098', 'HDFC0005678', '2025-01-25 18:48:22', '2025-01-25 18:48:22');

-- --------------------------------------------------------

--
-- Table structure for table `chats`
--

CREATE TABLE `chats` (
  `chat_id` int(11) NOT NULL,
  `sender_id` int(11) NOT NULL,
  `receiver_id` int(11) NOT NULL,
  `message` text NOT NULL,
  `status` enum('Sent','Delivered','Read') DEFAULT 'Sent',
  `sent_at` datetime DEFAULT current_timestamp(),
  `read_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `courses`
--

CREATE TABLE `courses` (
  `course_id` int(11) NOT NULL,
  `institution_id` int(11) NOT NULL,
  `course_name` varchar(255) NOT NULL,
  `course_description` text DEFAULT NULL,
  `fees_per_semester` decimal(10,2) DEFAULT NULL,
  `duration_in_months` int(11) DEFAULT NULL,
  `number_of_semesters` int(11) DEFAULT NULL,
  `even_semester_due_date` date DEFAULT NULL,
  `odd_semester_due_date` date DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `grantee_details`
--

CREATE TABLE `grantee_details` (
  `grantee_detail_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `father_name` varchar(255) DEFAULT NULL,
  `mother_name` varchar(255) DEFAULT NULL,
  `father_profession` varchar(255) DEFAULT NULL,
  `mother_profession` varchar(255) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `average_annual_salary` decimal(10,2) DEFAULT NULL,
  `rahbar_alumnus` enum('Y','N') DEFAULT 'N',
  `rcc_name` varchar(255) DEFAULT NULL,
  `course_applied` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `grantor_grantees`
--

CREATE TABLE `grantor_grantees` (
  `grantor_grantee_id` int(11) NOT NULL,
  `grantor_id` int(11) NOT NULL,
  `grantee_id` int(11) NOT NULL,
  `status` enum('Pending','Accepted','Declined') DEFAULT 'Pending',
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `grantor_grantees`
--

INSERT INTO `grantor_grantees` (`grantor_grantee_id`, `grantor_id`, `grantee_id`, `status`, `created_at`, `updated_at`) VALUES
(1, 5, 7, 'Accepted', '2025-01-25 18:48:22', '2025-01-27 03:18:43'),
(2, 6, 8, 'Accepted', '2025-01-25 18:48:22', '2025-01-25 18:48:22');

-- --------------------------------------------------------

--
-- Table structure for table `installment_details`
--

CREATE TABLE `installment_details` (
  `installment_id` int(11) NOT NULL,
  `year` year(4) NOT NULL,
  `installment_type` enum('Monthly','Quarterly','Half-Yearly','Yearly') NOT NULL,
  `deadline` date NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `institution`
--

CREATE TABLE `institution` (
  `institution_id` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `address` text DEFAULT NULL,
  `contact_person` text DEFAULT NULL,
  `designation` text DEFAULT NULL,
  `contact_email` varchar(255) DEFAULT NULL,
  `contact_phone` varchar(15) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `notifications`
--

CREATE TABLE `notifications` (
  `notification_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `message` text NOT NULL,
  `status` enum('Unread','Read') DEFAULT 'Unread',
  `notification_date` date DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `notifications`
--

INSERT INTO `notifications` (`notification_id`, `user_id`, `message`, `status`, `notification_date`, `created_at`) VALUES
(1, 7, 'Your payment has been received.', 'Unread', '2023-10-01', '2025-01-25 18:48:22'),
(2, 8, 'Please upload your progress report.', 'Unread', '2023-10-01', '2025-01-25 18:48:22');

-- --------------------------------------------------------

--
-- Table structure for table `payments`
--

CREATE TABLE `payments` (
  `payment_id` int(11) NOT NULL,
  `grantor_id` int(11) NOT NULL,
  `grantee_id` int(11) NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `payment_date` datetime DEFAULT current_timestamp(),
  `receipt_url` varchar(255) DEFAULT NULL,
  `status` enum('Pending','Received','Paid','Completed') DEFAULT 'Pending',
  `due_date` date DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `payments`
--

INSERT INTO `payments` (`payment_id`, `grantor_id`, `grantee_id`, `amount`, `payment_date`, `receipt_url`, `status`, `due_date`, `created_at`, `updated_at`) VALUES
(1, 5, 7, 5000.00, '2025-01-25 18:48:22', NULL, 'Paid', '2023-12-31', '2025-01-25 18:48:22', '2025-01-25 18:48:22'),
(2, 6, 8, 6000.00, '2025-01-25 18:48:22', NULL, 'Pending', '2023-12-31', '2025-01-25 18:48:22', '2025-01-25 18:48:22');

-- --------------------------------------------------------

--
-- Table structure for table `permissions`
--

CREATE TABLE `permissions` (
  `permission_id` int(11) NOT NULL,
  `permission_name` varchar(100) NOT NULL,
  `description` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `rcc_centers`
--

CREATE TABLE `rcc_centers` (
  `rcc_center_id` int(11) NOT NULL,
  `center_name` varchar(255) NOT NULL,
  `incharge_name` varchar(255) DEFAULT NULL,
  `contact_number` varchar(15) DEFAULT NULL,
  `location` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `roles`
--

CREATE TABLE `roles` (
  `role_id` int(11) NOT NULL,
  `role_name` varchar(50) NOT NULL,
  `description` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `roles`
--

INSERT INTO `roles` (`role_id`, `role_name`, `description`, `created_at`, `updated_at`) VALUES
(1, 'Super Admin', 'Overall control of the system', '2025-01-25 18:48:22', '2025-01-25 18:48:22'),
(2, 'Application Administrator', 'Day-to-day operations management', '2025-01-25 18:48:22', '2025-01-25 18:48:22'),
(3, 'Application Coordinator', 'Handling operational workflow and verification', '2025-01-25 18:48:22', '2025-01-25 18:48:22'),
(4, 'Convenor', 'Regional chapter administration', '2025-01-25 18:48:22', '2025-01-25 18:48:22'),
(5, 'Grantor', 'Financial support providers', '2025-01-25 18:48:22', '2025-01-25 18:48:22'),
(6, 'Grantee', 'Scholarship recipients', '2025-01-25 18:48:22', '2025-01-25 18:48:22'),
(7, 'Management', 'Strategic oversight and reporting', '2025-01-25 18:48:22', '2025-01-25 18:48:22');

-- --------------------------------------------------------

--
-- Table structure for table `role_permissions`
--

CREATE TABLE `role_permissions` (
  `role_permission_id` int(11) NOT NULL,
  `role_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `student_progress`
--

CREATE TABLE `student_progress` (
  `progress_id` int(11) NOT NULL,
  `grantee_id` int(11) NOT NULL,
  `marks` decimal(5,2) DEFAULT NULL,
  `file_path` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `student_progress`
--

INSERT INTO `student_progress` (`progress_id`, `grantee_id`, `marks`, `file_path`, `created_at`, `updated_at`) VALUES
(1, 7, 85.50, 'uploads/grantee1_progress1.pdf', '2025-01-25 18:48:22', '2025-01-25 18:48:22'),
(2, 8, 90.00, 'uploads/grantee2_progress1.pdf', '2025-01-25 18:48:22', '2025-01-25 18:48:22'),
(3, 7, 92.00, 'uploads/Md_Altamash.pdf', '2025-01-25 18:57:33', '2025-01-25 19:19:23');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `user_id` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `sex` enum('M','F') NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `phone` varchar(15) NOT NULL,
  `role_id` int(11) NOT NULL,
  `status` enum('Active','Inactive') DEFAULT 'Active',
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `region` varchar(100) NOT NULL DEFAULT 'Jeddah'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`user_id`, `name`, `email`, `sex`, `password_hash`, `phone`, `role_id`, `status`, `created_at`, `updated_at`, `region`) VALUES
(1, 'Super Admin', 'superadmin@rahbar.com', 'M', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '1234567890', 1, 'Active', '2025-01-25 18:48:22', '2025-01-25 18:48:22', 'Jeddah'),
(2, 'Application Admin', 'appadmin@rahbar.com', 'F', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '1234567891', 2, 'Active', '2025-01-25 18:48:22', '2025-01-25 18:48:22', 'Jeddah'),
(3, 'Application Coordinator', 'coordinator@rahbar.com', 'M', 'scrypt:32768:8:1$1Y8bjG9uDWqHZDhk$2b2cc1bb7387c3226fd8f6a12ae8a6a4ff060624144b7589c91fef678a401ed5d32d0c172100383ea73bfc247da135b38c91e241fd127b1a3b6dbfb17453256d', '1234567892', 3, 'Active', '2025-01-25 18:48:22', '2025-01-27 04:36:05', 'Jeddah'),
(4, 'Convenor', 'convenor@rahbar.com', 'F', 'scrypt:32768:8:1$iI6JQDMGhzowdgfg$c3ada7a316661ea90622bc3db4724c52ac12825cc93870e837ba043bfdec3e7defe1165a5ab3276091b1b65c13e2caf69d9da471dfe33b593a0b21d3bf181c9d', '1234567893', 4, 'Active', '2025-01-25 18:48:22', '2025-01-26 02:20:13', 'Jeddah'),
(5, 'Grantor 1', 'grantor1@rahbar.com', 'M', 'scrypt:32768:8:1$6z8YLwQCENu8VcC2$8c0331b95eae619e82a8154564956875dd5f9151ed18463aeb169f32fca0df4786bc42e7a4d123fab0aa833a513e903659ce1694372a48aa6d2da7957eaffc16', '1234567894', 5, 'Active', '2025-01-25 18:48:22', '2025-01-27 03:02:47', 'Jeddah'),
(6, 'Grantor 2', 'grantor2@rahbar.com', 'F', 'scrypt:32768:8:1$6z8YLwQCENu8VcC2$8c0331b95eae619e82a8154564956875dd5f9151ed18463aeb169f32fca0df4786bc42e7a4d123fab0aa833a513e903659ce1694372a48aa6d2da7957eaffc16', '1234567895', 5, 'Active', '2025-01-25 18:48:22', '2025-01-25 18:59:38', 'Jeddah'),
(7, 'Grantee 1', 'grantee1@rahbar.com', 'M', 'scrypt:32768:8:1$1PF75poMvzWR3qB9$2f32b0594eb1bc71669477e342b7bc0984fae02f849e0f198ab6cdd926a73ff3c069080874df84263de5b4c35300d161644f236c285c633bdf5c29e7d136e3b8', '1234567896', 6, 'Active', '2025-01-25 18:48:22', '2025-01-25 18:56:11', 'Jeddah'),
(8, 'Grantee 2', 'grantee2@rahbar.com', 'F', 'scrypt:32768:8:1$1PF75poMvzWR3qB9$2f32b0594eb1bc71669477e342b7bc0984fae02f849e0f198ab6cdd926a73ff3c069080874df84263de5b4c35300d161644f236c285c633bdf5c29e7d136e3b8', '1234567897', 6, 'Active', '2025-01-25 18:48:22', '2025-01-25 18:56:18', 'Jeddah'),
(9, 'Management', 'management@rahbar.com', 'M', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '1234567898', 7, 'Active', '2025-01-25 18:48:22', '2025-01-25 18:48:22', 'Jeddah'),
(12, 'unassigned', 'unassigned', 'M', 'fddscdfgvhhjbvkvbkjbl', '35461', 8, 'Active', '2025-01-27 02:54:38', '2025-01-27 02:54:38', 'Jeddah');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `approval`
--
ALTER TABLE `approval`
  ADD PRIMARY KEY (`approval_id`),
  ADD KEY `payment_id` (`payment_id`),
  ADD KEY `approver_id` (`approver_id`);

--
-- Indexes for table `bank_details`
--
ALTER TABLE `bank_details`
  ADD PRIMARY KEY (`bank_detail_id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `chats`
--
ALTER TABLE `chats`
  ADD PRIMARY KEY (`chat_id`),
  ADD KEY `sender_id` (`sender_id`),
  ADD KEY `receiver_id` (`receiver_id`);

--
-- Indexes for table `courses`
--
ALTER TABLE `courses`
  ADD PRIMARY KEY (`course_id`),
  ADD KEY `institution_id` (`institution_id`);

--
-- Indexes for table `grantee_details`
--
ALTER TABLE `grantee_details`
  ADD PRIMARY KEY (`grantee_detail_id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `grantor_grantees`
--
ALTER TABLE `grantor_grantees`
  ADD PRIMARY KEY (`grantor_grantee_id`),
  ADD KEY `grantor_id` (`grantor_id`),
  ADD KEY `grantee_id` (`grantee_id`);

--
-- Indexes for table `installment_details`
--
ALTER TABLE `installment_details`
  ADD PRIMARY KEY (`installment_id`);

--
-- Indexes for table `institution`
--
ALTER TABLE `institution`
  ADD PRIMARY KEY (`institution_id`);

--
-- Indexes for table `notifications`
--
ALTER TABLE `notifications`
  ADD PRIMARY KEY (`notification_id`),
  ADD KEY `user_id` (`user_id`);

--
-- Indexes for table `payments`
--
ALTER TABLE `payments`
  ADD PRIMARY KEY (`payment_id`),
  ADD KEY `grantor_id` (`grantor_id`),
  ADD KEY `grantee_id` (`grantee_id`);

--
-- Indexes for table `permissions`
--
ALTER TABLE `permissions`
  ADD PRIMARY KEY (`permission_id`);

--
-- Indexes for table `rcc_centers`
--
ALTER TABLE `rcc_centers`
  ADD PRIMARY KEY (`rcc_center_id`);

--
-- Indexes for table `roles`
--
ALTER TABLE `roles`
  ADD PRIMARY KEY (`role_id`);

--
-- Indexes for table `role_permissions`
--
ALTER TABLE `role_permissions`
  ADD PRIMARY KEY (`role_permission_id`),
  ADD KEY `role_id` (`role_id`),
  ADD KEY `permission_id` (`permission_id`);

--
-- Indexes for table `student_progress`
--
ALTER TABLE `student_progress`
  ADD PRIMARY KEY (`progress_id`),
  ADD KEY `grantee_id` (`grantee_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_id`),
  ADD UNIQUE KEY `email` (`email`),
  ADD UNIQUE KEY `phone` (`phone`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `approval`
--
ALTER TABLE `approval`
  MODIFY `approval_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `bank_details`
--
ALTER TABLE `bank_details`
  MODIFY `bank_detail_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `chats`
--
ALTER TABLE `chats`
  MODIFY `chat_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `courses`
--
ALTER TABLE `courses`
  MODIFY `course_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `grantee_details`
--
ALTER TABLE `grantee_details`
  MODIFY `grantee_detail_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `grantor_grantees`
--
ALTER TABLE `grantor_grantees`
  MODIFY `grantor_grantee_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `installment_details`
--
ALTER TABLE `installment_details`
  MODIFY `installment_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `institution`
--
ALTER TABLE `institution`
  MODIFY `institution_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `notifications`
--
ALTER TABLE `notifications`
  MODIFY `notification_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `payments`
--
ALTER TABLE `payments`
  MODIFY `payment_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `permissions`
--
ALTER TABLE `permissions`
  MODIFY `permission_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `rcc_centers`
--
ALTER TABLE `rcc_centers`
  MODIFY `rcc_center_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `roles`
--
ALTER TABLE `roles`
  MODIFY `role_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=8;

--
-- AUTO_INCREMENT for table `role_permissions`
--
ALTER TABLE `role_permissions`
  MODIFY `role_permission_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `student_progress`
--
ALTER TABLE `student_progress`
  MODIFY `progress_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `user_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2147483648;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `approval`
--
ALTER TABLE `approval`
  ADD CONSTRAINT `approval_ibfk_1` FOREIGN KEY (`payment_id`) REFERENCES `payments` (`payment_id`),
  ADD CONSTRAINT `approval_ibfk_2` FOREIGN KEY (`approver_id`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `bank_details`
--
ALTER TABLE `bank_details`
  ADD CONSTRAINT `bank_details_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `chats`
--
ALTER TABLE `chats`
  ADD CONSTRAINT `chats_ibfk_1` FOREIGN KEY (`sender_id`) REFERENCES `users` (`user_id`),
  ADD CONSTRAINT `chats_ibfk_2` FOREIGN KEY (`receiver_id`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `courses`
--
ALTER TABLE `courses`
  ADD CONSTRAINT `courses_ibfk_1` FOREIGN KEY (`institution_id`) REFERENCES `institution` (`institution_id`);

--
-- Constraints for table `grantee_details`
--
ALTER TABLE `grantee_details`
  ADD CONSTRAINT `grantee_details_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `grantor_grantees`
--
ALTER TABLE `grantor_grantees`
  ADD CONSTRAINT `grantor_grantees_ibfk_1` FOREIGN KEY (`grantor_id`) REFERENCES `users` (`user_id`),
  ADD CONSTRAINT `grantor_grantees_ibfk_2` FOREIGN KEY (`grantee_id`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `notifications`
--
ALTER TABLE `notifications`
  ADD CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `payments`
--
ALTER TABLE `payments`
  ADD CONSTRAINT `payments_ibfk_1` FOREIGN KEY (`grantor_id`) REFERENCES `users` (`user_id`),
  ADD CONSTRAINT `payments_ibfk_2` FOREIGN KEY (`grantee_id`) REFERENCES `users` (`user_id`);

--
-- Constraints for table `role_permissions`
--
ALTER TABLE `role_permissions`
  ADD CONSTRAINT `role_permissions_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `roles` (`role_id`),
  ADD CONSTRAINT `role_permissions_ibfk_2` FOREIGN KEY (`permission_id`) REFERENCES `permissions` (`permission_id`);

--
-- Constraints for table `student_progress`
--
ALTER TABLE `student_progress`
  ADD CONSTRAINT `student_progress_ibfk_1` FOREIGN KEY (`grantee_id`) REFERENCES `users` (`user_id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
