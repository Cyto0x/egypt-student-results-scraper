import requests
import threading
import queue
import re
import argparse
import time
import os
import json
import random
import sys
from collections import deque
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Configuration
DOMAINS = deque([
    "natega.dostor.org",
    "natega.elbalad.news",
    "natega.youm7.com",
    "natega.elwatannews.com",
    "natega.gomhuriaonline.com"
])

COMMON_HEADERS = {
    'Cache-Control': 'max-age=0',
    'Sec-Ch-Ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Linux"',
    'Accept-Language': 'en-US,en;q=0.9',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-User': '?1',
    'Sec-Fetch-Dest': 'document',
    'Accept-Encoding': 'gzip, deflate, br',
    'Priority': 'u=0, i'
}

# Domain-specific headers
HEADERS = {
    domain: {
        **COMMON_HEADERS,
        'Host': domain,
        'Origin': f'https://{domain}',
        'Referer': f'https://{domain}/' + ('?s=1' if domain in ['natega.dostor.org', 'natega.elbalad.news'] else '')
    }
    for domain in DOMAINS
}

# Regex patterns for data extraction
PATTERNS = {
    'seating_no': re.compile(
        r'<span[^>]*class="formatt3">\s*رقم الجلوس\s*</span>\s*<h1>\s*(\d+)\s*</h1>',
        re.IGNORECASE
    ),
    'name': re.compile(
        r'<span[^>]*class="formatt[^>]*>\s*الأسم:\s*</span>\s*<span>\s*([^<]+?)\s*</span>',
        re.IGNORECASE
    ),
    'status': re.compile(
        r'<span[^>]*class="formatt[^>]*>\s*حالة الطالب\s*:\s*</span>\s*<span>\s*([^<]+?)\s*</span>',
        re.IGNORECASE
    ),
    'education_type': re.compile(
        r'<span[^>]*class="formatt[^>]*>\s*نوعية التعليم\s*:\s*</span>\s*<span>\s*([^<]+?)\s*</span>',
        re.IGNORECASE
    ),
    'division': re.compile(
        r'<span[^>]*class="formatt[^>]*>\s*الشعبة\s*:\s*</span>\s*<span>\s*([^<]+?)\s*</span>',
        re.IGNORECASE
    )
}

# Thread-safe queue and locks
request_queue = queue.Queue()
print_lock = threading.Lock()
domain_lock = threading.Lock()
results_file_lock = threading.Lock()
state_lock = threading.Lock()

# Global variables
processed_count = 0
success_count = 0
failure_count = 0
captcha_count = 0
system_type = 2  # Default to old system (2)
active = True
last_id = 0
start_time = time.time()

# State management
STATE_FILE = "scraper_state.json"

def save_state():
    """Save current scraping state"""
    state = {
        'last_id': last_id,
        'processed': processed_count,
        'success': success_count,
        'failures': failure_count,
        'captchas': captcha_count,
        'system': system_type,
        'start_time': start_time
    }
    with state_lock:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)

def load_state():
    """Load scraping state if exists"""
    global last_id, processed_count, success_count, failure_count, captcha_count, system_type, start_time
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                last_id = state.get('last_id', 0)
                processed_count = state.get('processed', 0)
                success_count = state.get('success', 0)
                failure_count = state.get('failures', 0)
                captcha_count = state.get('captchas', 0)
                system_type = state.get('system', 2)
                start_time = state.get('start_time', time.time())
                return True
        except:
            return False
    return False

def clear_state():
    """Clear saved state"""
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

def get_next_domain():
    """Rotate domains in a thread-safe manner"""
    with domain_lock:
        DOMAINS.rotate(-1)
        return DOMAINS[0]

def extract_data(html):
    """Extract all available data using regex patterns"""
    result = {}
    for key, pattern in PATTERNS.items():
        match = pattern.search(html)
        if match:
            result[key] = match.group(1).strip()
    return result

def process_student(student_id):
    """Process a single student ID"""
    global processed_count, success_count, failure_count, captcha_count, last_id
    
    domain = get_next_domain()
    url = f'https://{domain}/Home/Natega'
    headers = HEADERS[domain]
    data = {'seating_no': student_id, 'system': system_type}
    
    try:
        response = requests.post(
            url,
            headers=headers,
            data=data,
            timeout=10,
            verify=False,
            allow_redirects=True
        )
        
        # Extract all possible data
        data = extract_data(response.text)
        
        if data.get('seating_no') and data.get('name'):
            # Successful extraction
            with print_lock:
                success_count += 1
                print(f"✅ {data['seating_no']} - {data['name']} [{domain}]")
                if 'status' in data:
                    print(f"   حالة الطالب: {data['status']}")
                if 'education_type' in data:
                    print(f"   نوعية التعليم: {data['education_type']}")
                if 'division' in data:
                    print(f"   الشعبة: {data['division']}")
            
            # Save to results file
            with results_file_lock:
                with open('results.csv', 'a', encoding='utf-8') as f:
                    fields = ['seating_no', 'name', 'status', 'education_type', 'division']
                    row = [str(data.get(field, 'N/A')) for field in fields]
                    f.write(','.join(row) + '\n')
        else:
            # Check for CAPTCHA
            if 'captcha' in response.text.lower() or 'recaptcha' in response.text.lower():
                with print_lock:
                    captcha_count += 1
                    print(f"⚠️ CAPTCHA detected for {student_id} on {domain}")
            else:
                with print_lock:
                    failure_count += 1
                    print(f"❌ Data not found for {student_id} on {domain}")
    except Exception as e:
        with print_lock:
            failure_count += 1
            print(f"🚨 Error for {student_id} on {domain}: {str(e)}")
    finally:
        processed_count += 1
        last_id = student_id
        save_state()

def worker():
    """Worker thread to process requests from queue"""
    while active:
        try:
            student_id = request_queue.get(timeout=2)
            process_student(student_id)
            request_queue.task_done()
            
            # Add small delay to prevent flooding
            time.sleep(random.uniform(0.05, 0.2))
        except queue.Empty:
            time.sleep(0.5)

def start_workers(num_threads):
    """Create and start worker threads"""
    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=worker)
        t.daemon = True
        t.start()
        threads.append(t)
    return threads

def calculate_speed():
    """Calculate requests per minute"""
    elapsed = time.time() - start_time
    if elapsed < 1:
        return 0
    return (processed_count / elapsed) * 60

def print_stats():
    """Print current statistics"""
    speed = calculate_speed()
    print("\n" + "="*50)
    print(f"Total processed: {processed_count}")
    print(f"Successful: {success_count} | Failures: {failure_count} | CAPTCHAs: {captcha_count}")
    print(f"Speed: {speed:.2f} requests/minute")
    print(f"Current system: {'نظام حديث' if system_type == 1 else 'نظام قديم'}")
    print("="*50)

def process_range(start_id, end_id, num_threads=20):
    """Process a range of student IDs"""
    global active, start_time
    
    # Clear previous state if not resuming
    if not load_state() or last_id == 0:
        # Initialize results file
        with open('results.csv', 'w', encoding='utf-8') as f:
            f.write("رقم الجلوس,الاسم,حالة الطالب,نوعية التعليم,الشعبة\n")
    
    # Add IDs to queue
    current_id = last_id + 1 if last_id > start_id else start_id
    for student_id in range(current_id, end_id + 1):
        request_queue.put(student_id)
    
    # Start worker threads
    threads = start_workers(num_threads)
    
    # Monitor progress
    try:
        while not request_queue.empty():
            time.sleep(1)
            print_stats()
    except KeyboardInterrupt:
        print("\nPausing... (Press Ctrl+C again to exit)")
        active = False
        for t in threads:
            t.join(timeout=1)
        save_state()
        sys.exit(0)
    
    # Wait for completion
    request_queue.join()
    active = False
    for t in threads:
        t.join()
    
    print_stats()
    print("Processing complete!")
    clear_state()

def process_single(student_id):
    """Process a single student ID"""
    process_student(student_id)
    print_stats()

def interactive_mode():
    """Interactive command interface"""
    global system_type, active
    
    print("\n" + "="*50)
    print("Egyptian Student Results Scraper")
    print("="*50)
    
    while True:
        print("\nOptions:")
        print("1. Fetch single student")
        print("2. Fetch range of students")
        print("3. Resume previous operation")
        print("4. Change system (Current: {'نظام حديث' if system_type == 1 else 'نظام قديم'})")
        print("5. View current stats")
        print("6. Exit")
        
        choice = input("\nEnter your choice: ")
        
        if choice == '1':
            try:
                student_id = int(input("Enter student ID: "))
                process_single(student_id)
            except ValueError:
                print("Invalid ID format!")
        
        elif choice == '2':
            try:
                start_id = int(input("Start ID: "))
                end_id = int(input("End ID: "))
                threads = int(input("Threads (10-30): ") or "20")
                threads = max(10, min(30, threads))
                process_range(start_id, end_id, threads)
            except ValueError:
                print("Invalid input format!")
        
        elif choice == '3':
            if load_state():
                print(f"Resuming from ID: {last_id}")
                end_id = int(input("Enter new end ID: ") or last_id + 100)
                threads = int(input("Threads (10-30): ") or "20")
                threads = max(10, min(30, threads))
                process_range(last_id, end_id, threads)
            else:
                print("No previous state found!")
        
        elif choice == '4':
            system_type = 1 if system_type == 2 else 2
            print(f"System changed to {'نظام حديث' if system_type == 1 else 'نظام قديم'}")
            save_state()
        
        elif choice == '5':
            print_stats()
        
        elif choice == '6':
            print("Exiting...")
            break
        
        else:
            print("Invalid choice!")

def main():
    """Main function"""
    global system_type
    
    parser = argparse.ArgumentParser(description='Egyptian Student Results Scraper')
    parser.add_argument('--number', type=int, help='Single student ID to fetch')
    parser.add_argument('--range', nargs=2, type=int, metavar=('START', 'END'), 
                        help='Range of student IDs to fetch')
    parser.add_argument('--resume', action='store_true', 
                        help='Resume previous operation')
    parser.add_argument('--system', choices=['0','1', '2'], default='0',
                        help='System type: 1 (نظام حديث) or 2 (نظام قديم) or 0 for both')
    parser.add_argument('--interactive', action='store_true',
                        help='Launch interactive mode')
    
    args = parser.parse_args()
    
    # Set system type
    system_type = int(args.system)
    
    # Initialize results file
    if not os.path.exists('results.csv'):
        with open('results.csv', 'w', encoding='utf-8') as f:
            f.write("رقم الجلوس,الاسم,حالة الطالب,نوعية التعليم,الشعبة\n")
    
    if args.interactive:
        interactive_mode()
    elif args.resume:
        if load_state():
            end_id = int(input("Enter new end ID: ") or last_id + 100)
            threads = int(input("Threads (10-30): ") or "20")
            process_range(last_id, end_id, threads)
        else:
            print("No previous state found!")
    elif args.number:
        process_single(args.number)
    elif args.range:
        start, end = args.range
        threads = min(30, max(10, (end - start) // 50 + 10))
        process_range(start, end, threads)
    else:
        print("Please specify an option or use --interactive")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        save_state()
        sys.exit(0)
