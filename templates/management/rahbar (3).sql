-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Mar 12, 2025 at 03:29 AM
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
-- Table structure for table `application_period`
--

CREATE TABLE `application_period` (
  `id` int(11) NOT NULL DEFAULT 1,
  `start_date` datetime DEFAULT NULL,
  `end_date` datetime DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `application_period`
--

INSERT INTO `application_period` (`id`, `start_date`, `end_date`, `is_active`) VALUES
(1, '2025-03-09 00:00:00', '2025-03-10 00:00:00', 1);

-- --------------------------------------------------------

--
-- Table structure for table `application_status`
--

CREATE TABLE `application_status` (
  `status_id` int(11) NOT NULL,
  `grantee_detail_id` int(11) NOT NULL,
  `status` enum('draft','submitted','interviewing','accepted','rejected','on hold','provisional admission letter','admitted') DEFAULT 'draft',
  `comments` text DEFAULT NULL,
  `updated_by` varchar(50) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `application_status`
--

INSERT INTO `application_status` (`status_id`, `grantee_detail_id`, `status`, `comments`, `updated_by`, `created_at`, `updated_at`) VALUES
(1, 2, 'interviewing', 'interview scheduled on 9th march', NULL, '2025-02-09 11:53:33', '2025-03-08 14:13:44'),
(3, 3, 'submitted', 'Application submitted', NULL, '2025-03-08 15:29:26', '2025-03-08 15:29:26'),
(4, 4, 'submitted', 'Application submitted', NULL, '2025-03-08 15:31:21', '2025-03-08 15:31:21');

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
  `user_id` varchar(50) NOT NULL,
  `bank_name` varchar(255) NOT NULL,
  `account_number` varchar(20) NOT NULL,
  `account_name` varchar(255) DEFAULT NULL,
  `ifsc_code` varchar(11) NOT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `bank_details`
--

INSERT INTO `bank_details` (`bank_detail_id`, `user_id`, `bank_name`, `account_number`, `account_name`, `ifsc_code`, `created_at`, `updated_at`) VALUES
(1, '7', 'State Bank of India', '123456', 'Grand', 'SBIN0001234', '2025-01-25 18:48:22', '2025-02-26 12:34:44'),
(2, '8', 'HDFC Bank', '987654321098', 'Grantee 2', 'HDFC0005678', '2025-01-25 18:48:22', '2025-02-23 04:39:09');

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
  `fees_per_semester` decimal(10,2) NOT NULL,
  `number_of_semesters` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `courses`
--

INSERT INTO `courses` (`course_id`, `institution_id`, `course_name`, `course_description`, `fees_per_semester`, `number_of_semesters`) VALUES
(1, 36526, 'd', 'd', 6300.00, 6),
(2, 58963, 'computer science and engineering', 'lorem ipsum', 65000.00, 8),
(3, 85, 'Chemical Engineering', 'CHemical engineering', 85000.00, 8);

-- --------------------------------------------------------

--
-- Table structure for table `deadlines`
--

CREATE TABLE `deadlines` (
  `deadline_id` int(11) NOT NULL,
  `frequency` enum('yearly','half-yearly','quarterly','monthly') NOT NULL,
  `deadline_date` date NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `deadlines`
--

INSERT INTO `deadlines` (`deadline_id`, `frequency`, `deadline_date`, `created_at`, `updated_at`) VALUES
(1, 'yearly', '2025-02-07', '2025-02-08 21:01:35', '2025-02-08 21:01:35');

-- --------------------------------------------------------

--
-- Table structure for table `grantee_details`
--

CREATE TABLE `grantee_details` (
  `grantee_detail_id` int(11) NOT NULL,
  `user_id` varchar(50) DEFAULT NULL,
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
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `father_mobile` varchar(15) NOT NULL,
  `mother_mobile` varchar(15) NOT NULL,
  `student_mobile` varchar(15) NOT NULL,
  `name` varchar(255) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `grantee_details`
--

INSERT INTO `grantee_details` (`grantee_detail_id`, `user_id`, `father_name`, `mother_name`, `father_profession`, `mother_profession`, `address`, `average_annual_salary`, `rahbar_alumnus`, `rcc_name`, `course_applied`, `created_at`, `updated_at`, `father_mobile`, `mother_mobile`, `student_mobile`, `name`) VALUES
(2, NULL, 'k', 'k', 'k', 'k', 'fwgwgwe', 500000.00, 'Y', 'a', 'd', '2025-02-09 17:23:33', '2025-03-08 20:32:58', '1234567890', '0123456789', '9587463215', 'Alta'),
(3, NULL, 'ka', 'kk', 'kaka', 'kakaka', 'yvbsdvxbiuvv  svbliuzv  uilbs vs sldgiufbls z', 5000.00, 'Y', 'jharkhand', 'computer science and engineering', '2025-03-08 20:59:26', '2025-03-08 21:01:41', '7586236985', '9632587412', '8259637410', 'alka'),
(4, NULL, 'haiVSB', 'gvierhg ', 'jlvs ', 'jezrhsvm', 'vwetsdcvkjbsldivuaewb fbaweaewhfp8aewui f aewifg ewfg aew8bweio7 fywi gaw9pf pwa9f wepfgqe83 ', 6000.00, 'Y', 'jharkhand', 'Chemical Engineering', '2025-03-08 21:01:21', '2025-03-08 21:01:21', '9632587456', '9876543214', '1230456789', 'altta');

-- --------------------------------------------------------

--
-- Table structure for table `grantor_grantees`
--

CREATE TABLE `grantor_grantees` (
  `grantor_grantee_id` int(11) NOT NULL,
  `grantor_id` varchar(50) NOT NULL,
  `grantee_id` varchar(50) NOT NULL,
  `status` enum('Pending','Accepted','Declined') DEFAULT 'Pending',
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `grantor_grantees`
--

INSERT INTO `grantor_grantees` (`grantor_grantee_id`, `grantor_id`, `grantee_id`, `status`, `created_at`, `updated_at`) VALUES
(1, '5', '7', '', '2025-01-25 18:48:22', '2025-03-10 00:07:20'),
(2, '6', '8', '', '2025-01-25 18:48:22', '2025-02-17 21:55:46');

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
-- Table structure for table `institutions`
--

CREATE TABLE `institutions` (
  `institution_id` int(11) NOT NULL,
  `institution_name` varchar(255) NOT NULL,
  `address` varchar(255) DEFAULT NULL,
  `contact_number` varchar(15) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `institutions`
--

INSERT INTO `institutions` (`institution_id`, `institution_name`, `address`, `contact_number`, `email`, `created_at`, `updated_at`) VALUES
(85, 'Bit Mesra', 'Ranchi', '7257863410', 'convenor@bitmesra.ac.in', '2025-02-26 08:38:49', '2025-02-26 08:38:49'),
(36526, 'as', 'as', '54', 'altamash3321@gmail.com', '2025-02-09 01:36:16', '2025-02-09 01:36:16'),
(58963, 'IIT Delhi', 'delhi', '9568432175', 'iit@iitdelhi.ac.in', '2025-02-26 06:53:51', '2025-02-26 06:53:51'),
(36526662, 'bkjb', 'bjb', '726', 'bhsbdks@gmail.com', '2025-02-09 12:57:41', '2025-02-09 12:57:41');

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
  `grantor_id` varchar(50) NOT NULL,
  `grantee_id` varchar(50) NOT NULL,
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
(1, '5', '7', 5000.00, '2025-01-25 18:48:22', 'aly', 'Paid', '2023-12-31', '2025-01-25 18:48:22', '2025-01-27 20:42:15'),
(2, '6', '8', 6000.00, '2025-01-25 18:48:22', 'aly', 'Pending', '2023-12-31', '2025-01-25 18:48:22', '2025-01-27 20:42:20'),
(3, '5', '7', 1000.00, '2025-01-27 21:18:29', 'uploads\\Md.Altamash07-01-2025.pdf', 'Paid', NULL, '2025-01-27 21:18:29', '2025-02-23 06:45:07'),
(4, '5', '7', 1000.00, '2025-02-26 12:32:51', 'uploads\\adhaar_card_2.pdf', 'Paid', NULL, '2025-02-26 12:32:51', '2025-02-26 12:46:32'),
(5, '5', '7', 0.00, '2025-03-12 06:39:44', NULL, 'Pending', '2025-07-12', '2025-03-12 06:39:44', '2025-03-12 06:39:44'),
(6, '6', '8', 0.00, '2025-03-12 06:39:44', NULL, 'Pending', '2025-07-12', '2025-03-12 06:39:44', '2025-03-12 06:39:44');

-- --------------------------------------------------------

--
-- Table structure for table `payment_due_dates`
--

CREATE TABLE `payment_due_dates` (
  `due_date_id` int(11) NOT NULL,
  `mapping_id` int(11) NOT NULL,
  `due_date` date NOT NULL,
  `status` enum('pending','paid','delayed') DEFAULT 'pending',
  `payment_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `payment_schedules`
--

CREATE TABLE `payment_schedules` (
  `schedule_id` int(11) NOT NULL,
  `frequency` enum('yearly','half-yearly','quarterly','monthly') NOT NULL,
  `amount` decimal(10,2) NOT NULL,
  `deadline_date` date NOT NULL,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `payment_schedules`
--

INSERT INTO `payment_schedules` (`schedule_id`, `frequency`, `amount`, `deadline_date`, `updated_at`) VALUES
(1, 'yearly', 12000.00, '2025-02-13', '2025-03-09 18:28:44'),
(2, 'half-yearly', 6000.00, '2025-02-14', '2025-03-09 18:28:44'),
(3, 'quarterly', 3000.00, '2025-02-15', '2025-03-09 18:28:44'),
(4, 'monthly', 2000.00, '2025-03-28', '2025-03-09 18:28:44');

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

--
-- Dumping data for table `rcc_centers`
--

INSERT INTO `rcc_centers` (`rcc_center_id`, `center_name`, `incharge_name`, `contact_number`, `location`, `created_at`, `updated_at`) VALUES
(1, 'a', 'a', '236', 'a', '2025-02-09 06:39:43', '2025-02-09 06:39:43'),
(2, 'jharkhand', 'tata', '9638527410', 'Ranchi', '2025-02-26 14:07:39', '2025-02-26 14:07:58');

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
(5, 'Sponsor', 'Financial support providers', '2025-01-25 18:48:22', '2025-02-09 14:21:22'),
(6, 'beneficiary', 'Scholarship recipients', '2025-01-25 18:48:22', '2025-02-09 14:22:29'),
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
  `grantee_id` varchar(50) NOT NULL,
  `marks` varchar(4) DEFAULT NULL,
  `file_path` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `student_progress`
--

INSERT INTO `student_progress` (`progress_id`, `grantee_id`, `marks`, `file_path`, `created_at`, `updated_at`) VALUES
(1, '7', '85.5', 'uploads/grantee1_progress1.pdf', '2025-01-25 18:48:22', '2025-01-25 18:48:22'),
(2, '8', '90.0', 'uploads/grantee2_progress1.pdf', '2025-01-25 18:48:22', '2025-01-25 18:48:22'),
(3, '7', '92.0', 'uploads/Md_Altamash.pdf', '2025-01-25 18:57:33', '2025-01-25 19:19:23');

-- --------------------------------------------------------

--
-- Table structure for table `system_config`
--

CREATE TABLE `system_config` (
  `config_id` int(11) NOT NULL DEFAULT 1,
  `fee_schedule` decimal(10,2) DEFAULT NULL,
  `deadline` date DEFAULT NULL,
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `user_id` varchar(50) NOT NULL,
  `name` varchar(255) NOT NULL,
  `email` varchar(255) NOT NULL,
  `sex` enum('M','F') NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `phone` varchar(15) NOT NULL,
  `role_id` int(11) NOT NULL,
  `status` enum('Active','Inactive','registered','recognised') DEFAULT 'Active',
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `region` varchar(100) NOT NULL DEFAULT 'Jeddah'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`user_id`, `name`, `email`, `sex`, `password_hash`, `phone`, `role_id`, `status`, `created_at`, `updated_at`, `region`) VALUES
('1', 'Super Admin', 'superadmin@rahbar.com', 'M', 'scrypt:32768:8:1$1Y8bjG9uDWqHZDhk$2b2cc1bb7387c3226fd8f6a12ae8a6a4ff060624144b7589c91fef678a401ed5d32d0c172100383ea73bfc247da135b38c91e241fd127b1a3b6dbfb17453256d', '1234567890', 1, 'Active', '2025-01-25 18:48:22', '2025-02-05 04:22:55', 'Jeddah'),
('12', 'unassigned', 'unassigned', 'M', 'fddscdfgvhhjbvkvbkjbl', '35461', 8, 'Active', '2025-01-27 02:54:38', '2025-01-27 02:54:38', 'Jeddah'),
('2', 'Application Admin', 'appadmin@rahbar.com', 'F', 'scrypt:32768:8:1$1Y8bjG9uDWqHZDhk$2b2cc1bb7387c3226fd8f6a12ae8a6a4ff060624144b7589c91fef678a401ed5d32d0c172100383ea73bfc247da135b38c91e241fd127b1a3b6dbfb17453256d', '1234567891', 2, 'Active', '2025-01-25 18:48:22', '2025-02-05 04:22:45', 'Jeddah'),
('3', 'Application Coordinator', 'coordinator@rahbar.com', 'M', 'scrypt:32768:8:1$1Y8bjG9uDWqHZDhk$2b2cc1bb7387c3226fd8f6a12ae8a6a4ff060624144b7589c91fef678a401ed5d32d0c172100383ea73bfc247da135b38c91e241fd127b1a3b6dbfb17453256d', '1234567892', 3, 'Active', '2025-01-25 18:48:22', '2025-01-27 04:36:05', 'Jeddah'),
('4', 'Convenor', 'convenor@rahbar.com', 'F', 'scrypt:32768:8:1$iI6JQDMGhzowdgfg$c3ada7a316661ea90622bc3db4724c52ac12825cc93870e837ba043bfdec3e7defe1165a5ab3276091b1b65c13e2caf69d9da471dfe33b593a0b21d3bf181c9d', '1234567893', 4, 'Active', '2025-01-25 18:48:22', '2025-02-26 14:01:08', 'Jeddah'),
('5', 'Grantor 1', 'grantor1@rahbar.com', 'M', 'scrypt:32768:8:1$6z8YLwQCENu8VcC2$8c0331b95eae619e82a8154564956875dd5f9151ed18463aeb169f32fca0df4786bc42e7a4d123fab0aa833a513e903659ce1694372a48aa6d2da7957eaffc16', '1234567894', 5, 'Active', '2025-01-25 18:48:22', '2025-03-10 00:07:13', 'Jeddah'),
('5698', 'Altamash', 'altamash3321@gmail.com', 'M', 'scrypt:32768:8:1$Z8WHlB9QPRFxqlYW$6496a44b301eec585e30d860d9150a0ceb1ef9013c4d39321d8ea169798186d6ec60f4c53a82616f46971852248b38b5b32e4049a2c1c948476cd816d6d03b2f', '7257830471', 2, 'Active', '2025-03-09 20:13:38', '2025-03-09 20:13:38', 'Jharkhand'),
('6', 'Grantor 2', 'grantor2@rahbar.com', 'F', 'scrypt:32768:8:1$6z8YLwQCENu8VcC2$8c0331b95eae619e82a8154564956875dd5f9151ed18463aeb169f32fca0df4786bc42e7a4d123fab0aa833a513e903659ce1694372a48aa6d2da7957eaffc16', '1234567895', 5, 'Active', '2025-01-25 18:48:22', '2025-02-17 21:55:40', 'Jeddah'),
('7', 'Grantee 1', 'grantee1@rahbar.com', 'M', 'scrypt:32768:8:1$1PF75poMvzWR3qB9$2f32b0594eb1bc71669477e342b7bc0984fae02f849e0f198ab6cdd926a73ff3c069080874df84263de5b4c35300d161644f236c285c633bdf5c29e7d136e3b8', '1234567896', 6, 'Active', '2025-01-25 18:48:22', '2025-01-25 18:56:11', 'Jeddah'),
('8', 'Grantee 2', 'grantee2@rahbar.com', 'F', 'scrypt:32768:8:1$1PF75poMvzWR3qB9$2f32b0594eb1bc71669477e342b7bc0984fae02f849e0f198ab6cdd926a73ff3c069080874df84263de5b4c35300d161644f236c285c633bdf5c29e7d136e3b8', '1234567897', 6, 'Active', '2025-01-25 18:48:22', '2025-01-25 18:56:18', 'Jeddah'),
('9', 'Management', 'management@rahbar.com', 'M', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', '1234567898', 7, 'Active', '2025-01-25 18:48:22', '2025-01-25 18:48:22', 'Jeddah'),
('M003-2025', 'MD ALTAMASH', 'ALTAMASH3328@GMAIL.COM', 'M', 'scrypt:32768:8:1$uv25cKrPf1BsYTXd$4088f77fbbea517bbf085f205ff52910da3385a89921aa898c6c6b06254fd12d29e6e21f3cedb5f67d2e8a81c1cee41aa479653509c83057ef48f05d2b76f324', '07257830471', 6, 'registered', '2025-03-11 18:06:11', '2025-03-11 20:24:25', 'Jeddah');

--
-- Triggers `users`
--
DELIMITER $$
CREATE TRIGGER `before_insert_role6` BEFORE INSERT ON `users` FOR EACH ROW BEGIN
    DECLARE next_id INT;
    DECLARE formatted_id VARCHAR(20);
    DECLARE current_year CHAR(4);
    
    -- Get the current year
    SET current_year = YEAR(CURDATE());
    
    -- Only trigger if role_id is 6
    IF NEW.role_id = 6 THEN
        
        -- Find the next number by counting existing role_id = 6
        SELECT COUNT(*) + 1 INTO next_id FROM users WHERE role_id = 6;
        
        -- Format the unique ID as M001/2024
        SET formatted_id = CONCAT('M', LPAD(next_id, 3, '0'), '/', current_year);
        
        -- Assign the generated unique ID
        SET NEW.user_id = formatted_id;
    END IF;
    
END
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `user_payment_mapping`
--

CREATE TABLE `user_payment_mapping` (
  `mapping_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `schedule_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `user_payment_mapping`
--

INSERT INTO `user_payment_mapping` (`mapping_id`, `user_id`, `schedule_id`) VALUES
(1, 4, 1),
(2, 5, 1),
(3, 6, 1);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `application_period`
--
ALTER TABLE `application_period`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `application_status`
--
ALTER TABLE `application_status`
  ADD PRIMARY KEY (`status_id`),
  ADD KEY `application_status_ibfk_1` (`grantee_detail_id`),
  ADD KEY `application_status_ibfk_2` (`updated_by`);

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
  ADD KEY `bank_details_ibfk_1` (`user_id`);

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
-- Indexes for table `deadlines`
--
ALTER TABLE `deadlines`
  ADD PRIMARY KEY (`deadline_id`),
  ADD UNIQUE KEY `frequency` (`frequency`);

--
-- Indexes for table `grantee_details`
--
ALTER TABLE `grantee_details`
  ADD PRIMARY KEY (`grantee_detail_id`),
  ADD KEY `grantee_details_ibfk_2` (`user_id`);

--
-- Indexes for table `grantor_grantees`
--
ALTER TABLE `grantor_grantees`
  ADD PRIMARY KEY (`grantor_grantee_id`),
  ADD KEY `grantor_grantees_ibfk_1` (`grantor_id`),
  ADD KEY `grantor_grantees_ibfk_2` (`grantee_id`);

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
-- Indexes for table `institutions`
--
ALTER TABLE `institutions`
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
  ADD KEY `payments_ibfk_1` (`grantor_id`),
  ADD KEY `payments_ibfk_2` (`grantee_id`);

--
-- Indexes for table `payment_due_dates`
--
ALTER TABLE `payment_due_dates`
  ADD PRIMARY KEY (`due_date_id`),
  ADD KEY `mapping_id` (`mapping_id`),
  ADD KEY `payment_id` (`payment_id`);

--
-- Indexes for table `payment_schedules`
--
ALTER TABLE `payment_schedules`
  ADD PRIMARY KEY (`schedule_id`),
  ADD UNIQUE KEY `frequency` (`frequency`);

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
  ADD KEY `student_progress_ibfk_2` (`grantee_id`);

--
-- Indexes for table `system_config`
--
ALTER TABLE `system_config`
  ADD PRIMARY KEY (`config_id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_id`),
  ADD UNIQUE KEY `email` (`email`),
  ADD UNIQUE KEY `phone` (`phone`);

--
-- Indexes for table `user_payment_mapping`
--
ALTER TABLE `user_payment_mapping`
  ADD PRIMARY KEY (`mapping_id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `schedule_id` (`schedule_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `application_status`
--
ALTER TABLE `application_status`
  MODIFY `status_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

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
  MODIFY `course_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- AUTO_INCREMENT for table `deadlines`
--
ALTER TABLE `deadlines`
  MODIFY `deadline_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `grantee_details`
--
ALTER TABLE `grantee_details`
  MODIFY `grantee_detail_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

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
-- AUTO_INCREMENT for table `institutions`
--
ALTER TABLE `institutions`
  MODIFY `institution_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=36526663;

--
-- AUTO_INCREMENT for table `notifications`
--
ALTER TABLE `notifications`
  MODIFY `notification_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `payments`
--
ALTER TABLE `payments`
  MODIFY `payment_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `payment_due_dates`
--
ALTER TABLE `payment_due_dates`
  MODIFY `due_date_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `payment_schedules`
--
ALTER TABLE `payment_schedules`
  MODIFY `schedule_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=13;

--
-- AUTO_INCREMENT for table `permissions`
--
ALTER TABLE `permissions`
  MODIFY `permission_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `rcc_centers`
--
ALTER TABLE `rcc_centers`
  MODIFY `rcc_center_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

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
-- AUTO_INCREMENT for table `user_payment_mapping`
--
ALTER TABLE `user_payment_mapping`
  MODIFY `mapping_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `application_status`
--
ALTER TABLE `application_status`
  ADD CONSTRAINT `application_status_ibfk_1` FOREIGN KEY (`grantee_detail_id`) REFERENCES `grantee_details` (`grantee_detail_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `application_status_ibfk_2` FOREIGN KEY (`updated_by`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

--
-- Constraints for table `approval`
--
ALTER TABLE `approval`
  ADD CONSTRAINT `approval_ibfk_1` FOREIGN KEY (`payment_id`) REFERENCES `payments` (`payment_id`);

--
-- Constraints for table `bank_details`
--
ALTER TABLE `bank_details`
  ADD CONSTRAINT `bank_details_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

--
-- Constraints for table `courses`
--
ALTER TABLE `courses`
  ADD CONSTRAINT `courses_ibfk_1` FOREIGN KEY (`institution_id`) REFERENCES `institutions` (`institution_id`);

--
-- Constraints for table `grantee_details`
--
ALTER TABLE `grantee_details`
  ADD CONSTRAINT `grantee_details_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

--
-- Constraints for table `grantor_grantees`
--
ALTER TABLE `grantor_grantees`
  ADD CONSTRAINT `grantor_grantees_ibfk_1` FOREIGN KEY (`grantor_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `grantor_grantees_ibfk_2` FOREIGN KEY (`grantee_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

--
-- Constraints for table `payments`
--
ALTER TABLE `payments`
  ADD CONSTRAINT `payments_ibfk_1` FOREIGN KEY (`grantor_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `payments_ibfk_2` FOREIGN KEY (`grantee_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

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
  ADD CONSTRAINT `student_progress_ibfk_2` FOREIGN KEY (`grantee_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE;

DELIMITER $$
--
-- Events
--
CREATE DEFINER=`root`@`localhost` EVENT `insert_recurring_payments` ON SCHEDULE EVERY 4 MONTH STARTS '2025-03-12 06:38:07' ON COMPLETION NOT PRESERVE ENABLE DO BEGIN
    INSERT INTO payments (grantor_id, grantee_id, amount, due_date, status)
    SELECT 
        grantor_id, 
        grantee_id, 
        0 AS amount,  -- Set initial amount to 0
        DATE_ADD(CURDATE(), INTERVAL 4 MONTH), 
        'Pending'
    FROM grantor_grantee;
END$$

DELIMITER ;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
