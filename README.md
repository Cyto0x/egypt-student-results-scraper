# Egyptian Student Results Scraper

A high-performance, multi-threaded Python tool for harvesting Egyptian student examination results from multiple official portals simultaneously.  
By rotating between 5+ result domains, it delivers 20–30× faster lookups than manual checking while reducing the risk of detection or IP blocking.

---

## Primary Goal
Efficiently collect comprehensive academic records for Egyptian students by scraping multiple official portals in parallel, with built-in anti-detection measures.

---

## Key Features
- **Parallelized Data Harvesting**
  - Scrapes multiple portals at once:
    - `natega.dostor.org`
    - `natega.elbalad.news`
    - `natega.youm7.com`
    - `natega.elwatannews.com`
    - `natega.gomhuriaonline.com`
  - Processes thousands of records in minutes.
  - Achieves significant speed improvements over manual lookups.

- **Anti-Detection System**
  - Automatic domain rotation to distribute requests.
  - Randomized request timing.
  - Header spoofing to mimic real browsers.
  - CAPTCHA detection and handling.

- **Comprehensive Data Extraction**
  - Seating number (always **7 digits**).
  - Student name.
  - Academic status (ناجح / راسب).
  - Education type (طلاب / طالبات).
  - Specialization (علمي علوم / أدبي).
  - Marks, percentage, school, and district.

- **Resilient Operation**
  - Resume scans after interruption.
  - Auto-switch domains if blocked.
  - State recovery after crashes.
  - **If any site is down, simply comment it out or remove it from the configuration list to keep the tool running smoothly.**

---

## Basic Usage

### Single Student Lookup (Auto Detect — Fetch Regardless of System)
```bash
python scraper.py --system 0 --number 1839300
```
### Range Processing (example: 10,000 records)
```bash
python scraper.py --system 1 --range 1839300 1849300
```

### Resume Interrupted Scan
```bash
python scraper.py --resume
```

### Interactive Mode
```bash
python scraper.py --interactive
```

---

## Output
Results are saved to:
```
results.csv
```
in UTF-8 encoding, with columns:
```
رقم الجلوس,الاسم,حالة الطالب,نوعية التعليم,الشعبة
```

---

## Legal Disclaimer
This tool is for educational and research purposes only.  
Use it responsibly and only on systems you have permission to access.  
Misuse of this software may violate applicable laws.

---

**GitHub Keywords:** scraping, egypt, education, students, results, multithreaded, automation, requests, regex, csv, data-extraction
