# Shruthi Jhari - Pages Documentation

This document describes every page in the Shruthi Jhari application, its purpose, core functionality, and how it fits into the overall academic support system.

The application has three user roles: Administrator, Facilitator, and Student. Each role has its own set of pages accessible through a sidebar or direct navigation. Authentication pages are shared across roles.

---

## 1. Splash Screen

File: pages/splash.py

Purpose
The very first screen that appears when the application launches. It introduces the brand and transitions the user into the app.

Key Elements
- Shruthi Jhari logo displayed at 180 pixels
- Application name and tagline
- Cascade gradient background
- Loading bar that fills over approximately 2.8 seconds
- Loading text that progresses through five stages
- Version number at the bottom
- Click anywhere to skip

Working
When the app starts, main.py calls show_page("splash"). The splash screen renders the logo and begins a loading animation using tkinter's after() method. The loading bar advances in fixed steps until it reaches completion, then automatically advances to the landing page. If the user clicks anywhere before that, it advances immediately.

MVP
Provides brand introduction and masks the initial data loading, giving a polished first impression.

---

## 2. Landing Page

File: pages/landing.py

Purpose
The public-facing home page shown before login. It showcases top performers and offers entry into the app.

Key Elements
- Branding: logo, app name, tagline
- Topper carousel that auto-slides every three seconds
- Carousel content: Overall Topper, Maths Topper, Physics Topper, Chemistry Topper, Computer Science Topper
- Previous and next navigation arrows
- Dot indicators for slide position
- Sign In and Register buttons (both in the top-right and in the bottom CTA row)
- Version footer

Working
The carousel reads its data from database.py using get_overall_topper() and get_subject_toppers(). It cycles automatically every three seconds and responds to manual arrow clicks. When a user clicks Sign In or Register, the router navigates to the respective auth page. The page also refreshes its topper data whenever it becomes visible again.

MVP
Public showcase of class performance and clear entry point for new and returning users.

---

## 3. Login Page

File: pages/auth/login.py

Purpose
Authenticates existing users and routes them to the correct dashboard based on their role.

Key Elements
- Email and password fields
- Password visibility toggle
- Sign In button with loading state
- Inline error messages
- Three demo account quick-fill buttons for Admin, Facilitator, and Student
- Back to landing link

Working
The user enters credentials or clicks a demo button to auto-fill them. On submit, the page queries the database for a matching user. It checks:
- Whether the user exists
- Whether the password matches
- Whether the account status is approved, pending, or rejected

If everything passes, app.set_user() is called. The router then looks at the user's role and navigates to admin_dashboard, fac_command, or stu_dashboard. Pending users get a message telling them to wait for approval. Rejected users get a message telling them to contact the administrator.

MVP
Single point of authentication for all roles with role-based routing.

---

## 4. Registration Page

File: pages/auth/register.py

Purpose
Allows new users to register as either a Student or Facilitator.

Key Elements
- Role selector with two options: Student and Facilitator
- Full name, email, password, and password confirmation
- USN, Grade, and Section fields that appear only for students
- Interest chips that appear only for students
- Inline validation errors
- Create account button
- Link to login

Working
The page dynamically shows or hides fields based on the selected role. When the user submits, the form performs client-side checks (name length, email format, password match, USN format) and database checks (no duplicate email, no duplicate USN). If validation passes, it inserts a new user row with status set to pending. Interests are saved into the user_interests table. On success, the page navigates to the pending page with the registered user's details.

MVP
Self-registration with admin approval, ensuring only verified users enter the system.

---

## 5. Pending Approval Page

File: pages/auth/pending.py

Purpose
Waiting screen for newly registered users while they await admin approval.

Key Elements
- Hourglass icon
- Registered user's avatar, name, email, and role chip
- Explanation of what happens next
- Live status line showing pending, approved, or rejected
- Back to home button
- Check now button

Working
The page polls the database every five seconds to check the user's status. If the status changes to approved, the page calls app.set_user() and the router takes the user to their dashboard. If the status changes to rejected, the user is sent back to registration. When the page is hidden or destroyed, polling stops cleanly to avoid background work.

MVP
Automatic unlock after approval, so users do not need to refresh or log in again manually.

---

## 6. Student Dashboard

File: pages/student/dashboard.py

Purpose
The main landing page for students after login. Shows a summary of their academic state at a glance.

Key Elements
- Hero card with avatar, name, USN, and current zone chip
- Overview KPI cards: latest IA average, attendance, badges earned, concepts mastered
- Today's Path card with the top recommended concept
- Upcoming reviews list (from the spaced repetition scheduler)
- Recent badges list
- Quick action tiles for eight sub-pages

Working
The dashboard pulls data from multiple sources:
- Marks summary and attendance from database.py
- Recommendations from models.recommender
- Reviews due from models.spaced_repetition
- Badge counts from models.badges

The zone ring around the avatar reflects the student's current color zone (Red, Yellow, Green, or Gold). Clicking Start Learning on Today's Path navigates to the learning screen with that concept preselected.

MVP
Single-glance overview that answers the question: what should I do today?

---

## 7. Student Profile

File: pages/student/profile.py

Purpose
A comprehensive 360-degree view of a single student.

Key Elements
- Large avatar with zone ring
- Name, USN, grade, section, interest chips
- Upload and remove profile photo buttons (for own profile)
- Marks summary table across all IAs
- Subject radar chart
- IA trend line chart
- Subject comparison bar chart
- Color journey showing how the student's zone changed across IAs
- Badges showcase wall with earned and locked badges
- Certificates list with Open PDF buttons
- Activities list with scores

Working
The page loads data from users, marks, marks_summary, color_history, user_badges, certificates, and activity_scores tables. It uses matplotlib charts from utils.charts to render the visual sections. The avatar upload button copies a selected image file into assets/avatars and clears the avatar cache to force a refresh. The page accepts a target_user_id parameter, so it can be used by facilitators to view any student.

MVP
Complete student portfolio combining marks, attendance, achievements, and learning progress.

---

## 8. Student Marks

File: pages/student/marks.py

Purpose
Detailed view of a student's internal assessment marks.

Key Elements
- Top stat cards: average across IAs, best IA, trend delta, best subject
- IA tabs for IA-1, IA-2, and IA-3
- Active IA section with a subject table and a gauge chart
- IA progression line chart
- Subject comparison bar chart
- Export report button

Working
The page loads marks_summary from the database for the selected IA. Clicking an IA tab switches the view instantly. Each subject row shows a progress bar and marks out of 100. The gauge shows the overall percentage for that IA colored by the student's zone. The export button calls export_student_report() from utils.excel_io to produce a four-sheet Excel file with marks, attendance, activities, and badges.

MVP
Clean, tabbed view of assessments with one-click export for parents or records.

---

## 9. Student Attendance

File: pages/student/attendance.py

Purpose
Visualizes the student's attendance record.

Key Elements
- Overall attendance percentage KPI
- Present, absent, and late counts
- Calendar heatmap of the last eight weeks
- Weekly attendance trend line
- Streak statistics: current streak, best streak, days missed
- Recent records table for the last fifteen days
- Export CSV button

Working
The page reads attendance rows for the last sixty days. The calendar heatmap is built as a grid of weeks (Monday to Sunday) with cell colors matching the status: green for present, amber for late, red for absent, blue for excused. Hovering a day updates a hint line with the exact date and status. Streaks are computed by walking backward from today through the present set.

MVP
Quick visual read of attendance patterns with drill-down details.

---

## 10. Student Learning Path

File: pages/student/learning_path.py

Purpose
Shows personalized content recommendations powered by the recommendation engine.

Key Elements
- Header stat strip: average mastery, concepts mastered, needs work, reviews due
- Today's Path card with the top recommendation and its reason
- Full ranked list of ten recommendations
- Reviews due section with quick-start buttons

Working
The page calls Recommender.todays_path() and Recommender.next_best() to obtain recommendations. Each recommendation includes a score computed from six weighted signals: mastery gap, prerequisite readiness, interest match, difficulty fit, spaced review timing, and freshness. Recommendations are sorted by score. The reason string explains why each item was chosen. Clicking any recommendation navigates to the learning screen for that concept.

MVP
Turns the recommendation engine's raw scores into a clear, human-readable path.

---

## 11. Learning Screen

File: pages/student/learning_screen.py

Purpose
The actual learning experience where students work through content items and answer questions.

Key Elements
- Top strip with question number, progress bar, and live mastery indicator
- Content card showing type badge, interest tag, title, and problem
- Answer input with Check button
- Three-level hint system (Nudge, Hint, Explain)
- Feedback line with correct or incorrect status
- Next button that unlocks after a correct answer
- Completion card after the last item

Working
Each content item is presented one at a time. For problems and quizzes, the student types an answer. The answer parser handles numbers, fractions, and percentages. When the student clicks Check, models.bkt.BKTTracker.update_from_attempt() records the attempt and updates the mastery probability. Hints are provided by utils.llm.get_hint(), which returns templated or LLM-generated guidance at three scaffolding levels. On completion, the spaced repetition scheduler records the review.

MVP
Interactive, adaptive learning loop that feeds the mastery model with every attempt.

---

## 12. Mastery Map

File: pages/student/mastery_map.py

Purpose
Visual grid of all concepts colored by mastery level.

Key Elements
- Overview stats: average mastery, mastered, developing, weak counts
- Legend row
- Concept tiles grouped by subject
- Concept detail modal on click

Working
The page uses BKTTracker.summary() to get the current mastery probability for every concept. Each tile shows mastery percentage, difficulty, and attempts. Tiles are colored by mastery label: red for weak, amber for developing, green for mastered. Clicking a tile opens a modal with more details including prerequisites, next review date, and a Practice button that navigates to the learning screen.

MVP
Immediate visual sense of where a student stands across the entire curriculum.

---

## 13. Student Activities

File: pages/student/activities.py

Purpose
Shows the student's performance on co-curricular activities.

Key Elements
- Top stats: total completed, average score, best score, types covered
- Filter chips by activity type
- Grid of completed activity cards
- Available activities section

Working
The page loads activity_scores for the student and joins with the activities table for metadata. Each card shows the activity name, type, score, percentage, progress bar, and completion date. The filter chips narrow the view to a specific activity type. The available section shows activities the student has not yet completed.

MVP
Co-curricular record that complements academic performance.

---

## 14. Student Badges

File: pages/student/badges.py

Purpose
Full showcase of earned and locked badges.

Key Elements
- Summary row with badge count, completion percentage, and progress bar
- Earned section with larger badge cards
- Locked section with unlock criteria
- Almost There section showing badges the student is close to earning

Working
The page uses BadgeEngine.progress_for_user() to get every badge with its earned or locked status. Earned badges show the unlock date. Locked badges show the criteri…
Paste above in Github, in Readme.md file..
