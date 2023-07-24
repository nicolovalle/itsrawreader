# itsrawreader


This is minimum bias raw file reader. 

---

python3. Packages needed: 
+ `docopt`
+ `os`
+ `sys`
+ `re`
+ `numpy` (only with `--fromdump`)

Usage:

```
./myrawreader.py --help
```

---

You can modify specific bytes in this way:

```
./myrawreader.py -f file.raw [any skimming option] > dump.txt
# edit dump.txt by hand
./embedfiles.py [-r file.raw] -d dump.txt [-o outfile.raw]
```

---
---

To make executable:

```
pip3 install pyinstaller
```

```
pyinstaller -F myrawreader.py
rm -fr build/
```

