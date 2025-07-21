# Lead Cleanup Suite

## Overview
The Lead Cleanup Suite is a comprehensive Streamlit-based application for processing and cleaning lead data. It provides multiple specialized tools for address standardization, DNC phone number management, data formatting, and lead generation workflows. This powerful suite helps clean, organize, and optimize lead data from CSV files with various output formats and processing options.

## Features

### 🏠 **Address Processing**
- Parses addresses using the `usaddress` library
- Expands directional, street type, and unit abbreviations
- Handles PO Box addresses
- Creates standardized address formats with city and state

### 📞 **Enhanced DNC Phone Number Cleaner**
- **Simple DNC Processing**: Remove phone numbers where DNC = 'Y'
- **Complex Pattern Support**: Handle comma-separated phone numbers with corresponding DNC statuses
- **Multi-Column Support**: Process multiple phone columns simultaneously
- **Pattern Examples**:
  - Simple: `Phone: '+1234567890', DNC: 'Y'` → Result: `Phone: ''`
  - Complex: `Phone: '+1111, +2222, +3333', DNC: 'N, Y, N'` → Result: `Phone: '+1111, +3333'`
- **Comprehensive Validation**: Automatic verification of DNC cleaning accuracy

### 🔧 **Data Processing Options**
- **Address + HoNWIncome**: Combine address with homeowner, net worth, and income range
- **Address + HoNWIncome First Name Last Name**: Add personal identifiers to homeowner data
- **Business Address + First Name Last Name**: Process business-focused contact data
- **ZIP Split**: Split data by ZIP codes with address and phone information
- **File Combiner and Batcher**: Merge multiple files and create manageable batches
- **Sha256**: Generate hashed email data for privacy compliance
- **Full Combined Address**: Comprehensive dataset with complete contact information
- **Phone & Credit Score**: Focus on phone numbers and credit scores with address details
- **Split by State**: Organize data by state for targeted campaigns
- **B2B Job Titles Focus**: Extract business-focused data with job titles and company info
- **Filter by Zip Codes**: Target specific geographic areas
- **Company Industry**: Filter data by industry classifications
- **Complete Contact Export**: Full contact dataset with all available information
- **Duplicate Analysis & Frequency Counter**: Identify and analyze duplicate records

### 📊 **Smart Format Detection**
- Automatically detects legacy and enhanced data formats
- Normalizes column structures for consistent processing
- Provides format-specific optimizations
- Handles format-specific fields appropriately

### ⚙️ **Advanced Settings**
- **Auto Address Cleaning**: Automatic address standardization
- **Phone Number Formatting**: Consistent phone number formatting
- **Batch Size Control**: Manage output file sizes (default: 2,000 rows)
- **Multiple Output Formats**: CSV, Excel, and JSON downloads
- **Preview Settings**: Configurable data preview options

## Requirements
- Python 3.x
- Required Libraries:
  - `streamlit`
  - `pandas` 
  - `usaddress`
  - `openpyxl` (for Excel output)
  - `io`
  - `zipfile`
  - `re`
  - `logging`
  - `gc` (for memory management)
  - `psutil` (optional, for memory monitoring)
  - `datetime`
  - `os`

You can install the dependencies using:
```bash
pip install streamlit pandas usaddress openpyxl psutil
```

## How to Use
1. **Start the application**:
   ```bash
   streamlit run app.py
   ```
2. **Upload your CSV file** containing lead data
3. **Configure settings** in the sidebar (optional):
   - Enable/disable auto address cleaning
   - Enable/disable phone number formatting  
   - Set batch size for large datasets
   - Configure preview settings
4. **Select processing option** from the available tools
5. **Configure option-specific settings** as needed
6. **Process your data** and download results in your preferred format

## Supported Data Formats

### Format Detection
The application can detect and process:
- **Classic Format**: Traditional column structure with standard fields
- **Enhanced Format**: Extended dataset with additional fields like UUID, skills, etc.
- **Custom Format**: Attempts to work with available columns in custom datasets

### Required Columns (varies by processing option)
**Basic Address Processing:**
- `PERSONAL_ADDRESS`, `PERSONAL_CITY`, `PERSONAL_STATE`

**DNC Phone Number Cleaner:**
- Any column with 'DNC' in the name (e.g., `DIRECT_DNC`, `MOBILE_PHONE_DNC`)
- Phone columns: `MOBILE_PHONE`, `DIRECT_NUMBER`, `PERSONAL_PHONE`, `COMPANY_PHONE`, `SKIPTRACE_B2B_PHONE`

**Complete Processing:**
- `FIRST_NAME`, `LAST_NAME`
- `PERSONAL_ADDRESS`, `PERSONAL_CITY`, `PERSONAL_STATE`, `PERSONAL_ZIP`
- Optional: `HOMEOWNER`, `NET_WORTH`, `INCOME_RANGE`, `CHILDREN`, `AGE_RANGE`
- Optional: `PERSONAL_EMAIL`, `BUSINESS_EMAIL`, `LINKEDIN_URL`
- Optional: Phone and DNC columns

### Output Formats
- **CSV**: Standard comma-separated values
- **Excel**: .xlsx format with formatting
- **JSON**: Structured data format
- **ZIP**: Multiple files organized by criteria (ZIP codes, states, etc.)

## DNC Phone Number Cleaner Usage

### Simple DNC Processing
```
Input Data:
MOBILE_PHONE: "+1234567890"
DNC: "Y"

Result:
MOBILE_PHONE: "" (phone removed)
```

### Complex Comma-Separated Processing  
```
Input Data:
MOBILE_PHONE: "+1111111111, +2222222222, +3333333333"
MOBILE_PHONE_DNC: "N, Y, N"

Result: 
MOBILE_PHONE: "+1111111111, +3333333333" (middle phone removed)
```

### Supported DNC Patterns
- **Simple**: `'Y'`, `'N'`, `'YES'`, `'NO'`, `'TRUE'`, `'FALSE'`
- **Complex**: `'N, Y, N'`, `'Y, N, Y, N'` (comma-separated lists)
- **Fallback**: Any value containing 'Y' will trigger phone removal

## Performance Enhancements
- **Memory Management**: Automatic garbage collection for large datasets
- **Chunk Processing**: Processes large files in manageable chunks
- **Progress Tracking**: Visual progress indicators during processing
- **Responsive UI**: Mobile-friendly interface with optimized controls

## Troubleshooting

### Common Issues
1. **Missing Columns**: Ensure your CSV contains the required columns for your selected processing option
2. **DNC Column Not Found**: The app automatically detects columns with 'DNC' in the name
3. **Large Files**: Use the batch size setting to split large datasets into manageable chunks
4. **Phone Format Issues**: Enable "Format Phone Numbers" in settings for consistent formatting

### Performance Tips
- For large files (>10,000 rows), consider using batch processing
- Enable auto address cleaning only when necessary for better performance
- Use ZIP or state splitting for very large datasets

## Acknowledgments
This project utilizes:
- `usaddress` library for parsing and structuring address components
- `streamlit` for the web interface
- `pandas` for data processing and manipulation

## License
This project is licensed under the MIT License.

