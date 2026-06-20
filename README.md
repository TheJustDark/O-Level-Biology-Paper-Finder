O-Level Biology Past Paper Finder (Syllabus 5090)
A desktop utility designed to streamline the study and revision process for Cambridge O-Level Biology (5090). This application automatically downloads past papers from PapaCambridge, indexes them dynamically, and provides a clean graphical user interface (GUI) to locate and open Question Papers (QP) and Mark Schemes (MS) side-by-side with just a few clicks.
Features
- **Automated Crawler & Scraper (`Scrapper.py`)**: Uses Undetected Chromedriver and requests sessions to bypass security challenges and download past papers for specified year ranges.
- **Background Auto-Sync**: The GUI automatically triggers the cataloging logic on startup. It scans the downloaded folder, verifies file integrity, pairs QPs with MSs, and updates the local JSON database without manual command-line intervention.
- **Dynamic Cascade Dropdowns**: Select a Year, and the Session dropdown dynamically updates. Select a Session, and only the published Variants for that specific exam are shown. This prevents search errors.
- **Cross-Platform PDF Launcher**: Opens selected documents automatically using your system's default PDF viewer on Windows, macOS, or Linux.

Project Structure
O-Level-Biology-Paper-Finder/
│
├── papers/                      # Locally downloaded PDFs (auto-generated, ignored by Git)
├── .gitignore                   # Prevents massive PDF folders from uploading to Git
├── Cleanup_and_Inventory.py     # Parses filenames and updates the database
├── GUI_Answer.py                # Main user interface (Run this to search papers)
├── Success.py                   # Scraping engine to download new papers
└── inventory.json               # Local database mapping the papers (auto-updated)

Setup and Installation
Prerequisites
Make sure you have Python installed (Python 3.10+ recommended). You will also need Google Chrome installed on your computer for the scraper to work.

Step 1: Install Dependencies
Open your terminal or command prompt and install the required Python libraries:
pip install undetected-chromedriver selenium requests

Step 2: Download the Papers (Scraper)
To download the papers to your local drive, run the scraper script.
Note: This only needs to be run once initially, or when you want to update your directory with newer papers.
Run python Success.py

Step 3: Run the Finder Application
Once you have papers downloaded, launch the main application. The script will automatically organize the newly downloaded PDFs in the background and open the interface:
Run python GUI_Answer.py

License
This project is open-source and intended purely for personal and educational revision purposes.
