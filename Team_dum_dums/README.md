\# Team Name: dum dums



\## Members:

\- Purvika Reddy MK

\- Subhashini B



\## Problem Statement / Company:

PROBLEM STATEMENT:

Acceleron Labs works extensively with government tenders which have

detailed product requirements and specifications.

These specifications cover both hardware requirements (eg.CPU, RAM,

storage capacity etc.) and software requirements (eg. Protocols, security \&

access control, system logs etc.)

Currently, analysing these specifications manually can lead to errors and

inefficiencies.

There is a need for software-driven solution to automate this process.

The solution should:

1\. Extract and identify hardware requirements separately.

2\. Extract and identify software requirements separately.

3\. Handle input files primarily in PDF format, and occasionally Excel

(XLS) format.

structured Excel file .

The extracted information should be organized and exported into a

Since requirement formats vary across documents, the system must be

capable of interpreting different representations and writing styles.

Few sample requirements have been shared. In these samples, you can see

that Hardware and Software requirements are represented in different

ways.

The software should be able to decode them and arrive at the result.

ANY LLM MODELS OR API KEYS CAN BE USED  (Google Gemini and Claude

are some examples for LLMs



The Augmented Tech Stack (Genesis Recommended)

Frontend / UI: v0 by Vercel – Quickly build interfaces for uploading

documents and visualizing extracted requirements without spending

time on UI development.

Backend / IDE: Windsurf – Ideal for handling file parsing logic, NLP

pipelines, and API development efficiently using AI-assisted coding.

Database \& BaaS: Supabase – Store extracted structured data, logs, and

processed outputs with ready-to-use APIs.

Rapid Prototyping: Bolt.new – Enables quick setup of full-stack

applications to test document processing workflows end-to-end



Company: Acceleron labs



\## Tech Stack:

* Frontend / UI: v0 by Vercel
* Backend / IDE: FastAPI and Uvicorn



\## Project Description:

The system automatically detects file type and selects the appropriate extraction method (PyMuPDF, pdfplumber, or OCR). Extracted content is processed using an LLM to generate clean, structured outputs. Results are standardized into tabular format and exported to Excel. Designed for robustness, scalability, and handling real-world unstructured documents.

## PPT has been uploaded
## video link: https://drive.google.com/file/d/1t8LEHnlIvZngKms9maGgEwb4udsRKOaT/view?usp=sharing

