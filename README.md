# makeup

...the Holy Bible in languages!

```
‘Let there be light,’
“Khuavak om hen,”
“လင်းဖြစ်စေ”
«Det bli lys!»
‹String›
`String`
haven`t, doesn`t
ÆØÅ,æøå
```

# task

- taskIdentify: `xml`, `json`, `ph4`
- taskName: `(tedim1932)`, `fill`, `todo:`, `all:`, `list:`
- taskOption: `none/any`

```
node bible {taskIdentify} {taskName} {taskOption}
```

# taskIdentify: `json`

```shell
node bible json tedim1932
node bible json fill
node bible json all:sqlite
```

# taskIdentify: `xml`

```shell
node bible xml tedim1932 true
node bible xml list:tedim1932 true
node bible xml fill true
node bible xml all:json true
```

# taskIdentify: `ph4`

```shell
node bible ph4 fi-fi42.1642 true
node bible ph4 list:fi-fi42.1642,fi-fi42d.1642,fi-fi76.1776,fi-fi76a.1776,fi-fi76d.1776,fi-fik38.1938,fi-fik76.1776,fi-kinb.1938,fi-kr.1992,fi-rk12.2002 true
node bible ph4 list:fi-fi42.1642,fi-fi42d.1642,fi-fi76.1776,fi-fi76a.1776,fi-fi76d.1776 true

node bible ph4 list:my-bjb.1840,my-burb.1825,my-jb.1933,my-mcl.2005,my-msb.2017 true

node bible ph4 list:no-dnb.1930,no-n11.2011,no-n11nn.2011,no-n78.1978,no-n78nn.1985,no-nb.2007,no-smb.1921 true

node bible ph4 list:sv-dnf.2014,sv-kxii.1873,sv-nub15.2015,sv-s17.1917,sv-sb00.2000,sv-sbd00.2000,sv-sfb.1998,sv-sfb15.2015,sv-sfb98.1998,sv-sv17.1917 true
```

# taskName: `todo`

```shell
node bible ph4 todo:
node bible ph4 todo:fi-fi42.1642,fi-fi42d.1642,fi-fi76.1776,fi-fi76a.1776,fi-fi76d.1776
```



## Verse merge
```shell
<verse id="([0-9]+-[0-9]+)"
<verse id="([0-9]+)-([0-9]+)"
<verse id="\1" merge="\2"


<book id="(.+?)">(.*?)</info>


<book id="(.+?)" name="" shortname="">
  <info id="name">(.+?)</info>
  <info id="shortname">(.+?)</info>
<book id="(.*)" name="" shortname="">\n\t\t<info id="name">(.*)</info>\n\t\t<<info id="shortname">(.*)</info>

<book id="$1" name="$2" shortname="$3">

<book id="(.*)" name="" shortname="">

<book id="(.*)" name="" shortname="">
		<info id="name">(.*)</info>
		<info id="shortname">(.*)</info>
<book id="\1" name="\2" shortname="\3">

<book id="([0-9]+)" name="" shortname="">
		<info id="name">(.*)</info>
		<info id="shortname">(.*)</info>

```
Error:
  finish1938
  swedish1917

https://www.ph4.org/b4_index.php
danish1933 missing alots

npm link
