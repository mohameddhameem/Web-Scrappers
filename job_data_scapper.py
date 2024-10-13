from playwright.sync_api import sync_playwright
import time
import pandas as pd
import os
import numpy as np

def scrape_job_list(page):
    jobs = page.query_selector_all('.JobCard__card___22xP3')
    print(f"Number of job cards found: {len(jobs)}")

    job_data = []
    for index, job in enumerate(jobs):
        print(f"\nScraping job card {index + 1}:")
        
        # Extract job URL
        job_url = job.get_attribute('href')
        full_job_url = f"https://www.mycareersfuture.gov.sg{job_url}" if job_url else 'N/A'
        
        # Extract other data points
        company_name = job.query_selector('.JobCard__job-title-flex___2R-sW p.f6.fw6')
        company_name = company_name.inner_text() if company_name else 'N/A'
        
        job_title = job.query_selector('[data-testid="job-card__job-title"]')
        job_title = job_title.inner_text() if job_title else 'N/A'
        
        location = job.query_selector('[data-testid="job-card__location"]')
        location = location.inner_text() if location else 'N/A'
        
        employment_type = job.query_selector('[data-testid="job-card__employment-type"]')
        employment_type = employment_type.inner_text() if employment_type else 'N/A'
        
        seniority = job.query_selector('[data-testid="job-card__seniority"]')
        seniority = seniority.inner_text() if seniority else 'N/A'
        
        category = job.query_selector('[data-testid="job-card__category"]')
        category = category.inner_text() if category else 'N/A'
        
        skills_matched = job.query_selector('[data-testid="skill-matched-desc"]')
        skills_matched = skills_matched.inner_text() if skills_matched else 'N/A'
        
        applications = job.query_selector('[data-testid="job-card__num-of-applications"]')
        applications = applications.inner_text() if applications else 'N/A'
        
        posting_date = job.query_selector('[data-cy="job-card-date-info"]')
        posting_date = posting_date.inner_text() if posting_date else 'N/A'
        
        salary_range = job.query_selector('[data-testid="salary-range"]')
        salary_range = salary_range.inner_text().replace('\n', ' ') if salary_range else 'N/A'
        
        salary_type = job.query_selector('[data-testid="salary-type"]')
        salary_type = salary_type.inner_text() if salary_type else 'N/A'
        
        logo_img = job.query_selector('.JobCard__image___qnJmz img')
        logo_url = logo_img.get_attribute('src') if logo_img else 'N/A'

        # Compile all data into a dictionary
        job_info = {
            'Company Name': company_name,
            'Job Title': job_title,
            'Job URL': full_job_url,
            'Location': location,
            'Employment Type': employment_type,
            'Seniority': seniority,
            'Category': category,
            'Skills Matched': skills_matched,
            'Applications': applications,
            'Posting Date': posting_date,
            'Salary Range': salary_range,
            'Salary Type': salary_type,
            'Logo URL': logo_url
        }

        job_data.append(job_info)

    return job_data

def extract_job_details(page, url):
    page.goto(url)
    time.sleep(2)  # Wait for content to load

    def safe_extract(selector, attribute='inner_text'):
        elements = page.locator(selector).all()
        if not elements:
            return 'N/A'
        if len(elements) == 1:
            return getattr(elements[0], attribute)()
        return ' | '.join([getattr(elem, attribute)() for elem in elements])

    return {
        "Job ID": safe_extract('span[data-testid="job-details-info-job-post-id"]'),
        # "Location (Detailed)": safe_extract('p[data-testid="job-details-info-location-map"] a'),
        "Employment Type (Detailed)": safe_extract('p[data-testid="job-details-info-employment-type"]'),
        "Seniority (Detailed)": safe_extract('p[data-testid="job-details-info-seniority"]'),
        "Experience": safe_extract('p[data-testid="job-details-info-min-experience"]'),
        "Categories (Detailed)": safe_extract('p[data-testid="job-details-info-job-categories"]'),
        "Salary Range (Detailed)": safe_extract('span[data-testid="salary-range"]'),
        "Salary Type (Detailed)": safe_extract('span[data-testid="salary-type"]'),
        "Applications (Detailed)": safe_extract('span[data-testid="job-details-info-num-of-applications"]'),
        "Posting Date (Detailed)": safe_extract('span[data-testid="job-details-info-last-posted-date"]'),
        "Closing Date": safe_extract('span[data-testid="job-details-info-job-expiry-date"]')
    }

def scrape_job_listings(page_numbers):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        base_url = "https://www.mycareersfuture.gov.sg/search?search=Data%20Science&sortBy=new_posting_date&page="
        all_job_data = []

        for page_num in page_numbers:
            url = f"{base_url}{page_num}"
            print(f"Scraping page {page_num}...")
            page.goto(url)
            time.sleep(2)  # Wait for content to load

            job_data = scrape_job_list(page)
            all_job_data.extend(job_data)

            print(f"Scraped {len(job_data)} jobs from page {page_num}")

        browser.close()

    # Save initial job list to CSV
    df = pd.DataFrame(all_job_data)
    df.to_csv('2_job_data_initial.csv', index=False)
    print(f"Initial data for {len(all_job_data)} jobs has been scraped and saved to job_data_initial.csv")

def scrape_detailed_job_info(df):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for index, row in df.iterrows():
            print(f"Extracting detailed information for job {index + 1}/{len(df)}: {row['Job Title']}")
            job_details = extract_job_details(page, row['Job URL'])
            
            # Update the DataFrame with the new information
            for key, value in job_details.items():
                df.at[index, key] = value

        browser.close()

    # Save the updated data to a new CSV
    df.to_csv('2_job_data_detailed.csv', index=False)
    print(f"Detailed data for {len(df)} jobs has been scraped and saved to job_data_detailed.csv")

def main(page_numbers):
    # Check if job_data_initial.csv exists
    if os.path.exists('2_job_data_initial.csv'):
        print("job_data_initial.csv found. Using existing data.")
        df = pd.read_csv('2_job_data_initial.csv')
    else:
        print("job_data_initial.csv not found. Scraping job listings...")
        scrape_job_listings(page_numbers)
        df = pd.read_csv('2_job_data_initial.csv')

    # Scrape detailed job information
    scrape_detailed_job_info(df)

if __name__ == "__main__":
    pages_to_scrape = np.arange(17) # [0, 1, 2, 3, 4, 5]  # This will scrape pages 0 to 5
    main(pages_to_scrape)