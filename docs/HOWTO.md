# HOWTO

# Parsing and importing

You can parse and import your data (transactions and accounts for now) with two steps:
1. Parse from source directory to an standard directory
2. Import from standard directory

```bash
# Parse transaction files from a import directory
$ ./manage.py parse_data --source-dir <import-dir> --dest-dir <import-dir-parsed>

# Import standard transactions files from the import directory
$ ./manage.py import_data --source-dir <import-dir-parsed>
```

We required the (unparsed) import directory to contain .csv files with a certain and in a certain directory structure:

```bash
# Import directory Structure:
<your-unparsed-import-directory>/
├── Accounts.csv  # Optional
├── <InstitutionName>__<AccountID>/
│   ├── <some-transaction-file-name-1>.csv
│   ├── ...
│   └── <some-transaction-file-name-n>.csv
├── ...
└── <InstitutionName>__<AccountID>/
    ├── <some-transaction-file-name-1>.csv
    ├── ...
    └── <some-transaction-file-name-2>.csv

# Accounts.csv file Format:
AccountID: str
Name: str
Institution: "KOHO" | "TDCanada"
AmountInitial: float
DateStart: YYYY-MM-DD

# The format of transaction csv files will depend on the institution. TDCanada for example
# is expected to look like this:
# TDCanada__<AccountID>/<some-transaction-file-name-x>.csv
(No Header)
<MM/DD/YYYY>,<Some-Non-Unique-Transaction-Name>,<Amount-Out>,<Amount-In>,<Balance>

# Example:
$ cat some-unparsed-import-directory/TDCanada__Chequing_1234/accountactivity-2022-01.csv
01/04/2022,PAYPAL *DOORDAS   _V,26.68,,12345.67
01/05/2022,PAYPAL *UBER      _V,4.52,,12341.15
```

The standard import directory will contain .csv files with a certain and in a certain directory structure:

```bash
# Import directory Structure:
<your-import-source-directory>/
├── Accounts.csv
└── Transactions
    ├── <InstitutionName>__<AccountID>__<YYYY>-<MM>.csv
    ├── ...
    └── <InstitutionName>__<AccountID>__<YYYY>-<MM>.csv

# Accounts.csv file Format:
AccountID: str
Name: str
Institution: "KOHO" | "TDCanada"
AmountInitial: float
DateStart: YYYY-MM-DD

# Transactions/<InstitutionName>__<AccountID>__<YYYY-MM-DD>.csv file Format:
Date: YYYY-MM-DD
TransactionID: str
TransactionIDRaw: str
Amount: float

# Examples:

# Import Folder Example:
$ tree .input-dir/
.input-dir/
├── Accounts.csv
└── Transactions
    ├── KOHO__ABC__2020-03.csv
    ├── KOHO__ABC__2020-04.csv
    ├── TDCanada__Chequing_12345__2020-01.csv
    ├── TDCanada__Chequing_12345__2020-02.csv
    ├── TDCanada__Chequing_12345__2020-03.csv
    ├── TDCanada__Chequing_12345__2020-04.csv
    ├── TDCanada__Savings_789__2020-01.csv
    ├── TDCanada__Savings_789__2020-02.csv
    ├── TDCanada__Savings_789__2020-03.csv
    └── TDCanada__Savings_789__2020-04.csv

# Accounts.csv file Example:
$ cat .input-dir/Accounts.csv | column -t -s ','
AccountID        Name                      Institution  AmountInitial  DateStart
PrepaidCard_ABC  Koho Prepaid Credit Card  KOHO         0.00           2020-01-05
Chequing_1234    TD Chequing Account       TDCanada     1000.00        2020-01-05
Savings_567      TD Savings Account        TDCanada     5000.00        2020-03-20

# Transactions/<Institution-Name>__<Account-AccountID>__<YYYY-MM-dd>.csv file Example:
$ cat .input-dir/Transactions/TD__Chequing_1234__2020-01.csv | column -t -s,
Date        TransactionName  Amount
2020-01-01  ABC XYZ          -50.04
2020-01-01  PQR__ _ABC       -13.33
2020-01-02  WXY AAA          100.00
2020-01-20  PAYROLL          5000.00
```
The data in the directory can imported into the system with a single command:

```bash
./manage.py import_data --source-dir <url-or-path/to/directory>

# Example 1: Upload from local directory:
./manage.py import_data --source-dir /home/my-user/my-import-directory/

# Example 2: Upload from S3:
./manage.py import_data --source-dir s3://my-bucket/my-import-directory/
```

Example Output:
```bash
$ ./manage.py import_data --source-dir .input-dir/
Directory structure and file formats are valid, proceed with import
Imported accounts [created: 3, updated: 0]
Imported transactions [created: 4, updated: 0]
```