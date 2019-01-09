# makeup
«Det bli lys!»
“Khuavak om hen,”
‘Na pa in kote tungah hong suat vangik zangsak in,’
‹String›

# Verse merge
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