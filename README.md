# Bible@laisiangtho

...the Holy Bible in languages!

```bash
Let there be light
Khuavak om hen
အ​လင်း​ဖြစ်​စေ
Det bli lys
```

... symbol

```bash
‘String’
“String”
“String”
«String»
‹String›
`String`
haven`t, doesn`t
ÆØÅ,æøå
```

| Name | Language | ISO |
| --- | --- | --- |
| Baibal Thianghlim (Falam) | Falam, Lai, Chin | cfm |
| Baibal Thiang (Hakha) | Hakha, Lai, Chin | cnh |
| Pathian Lehkhabu Thianghlim (Mizo) | Mizo, Lushai, Chin | lus |
| Common Language Bible (Mizo) | Mizo, Lushai | lus |
| Paite Bible (Paite) | Paite, Zolai, Chin | pck |
| Lai Siangtho (Sizang) | Sizang, Zolai, Chin, Siyin | csy |
| Lai Siangtho (Tedim) | Tedim, Zolai, Chin | ctd |
| Khazopa Chabu Pathaipa (Mara) | Mara, Chin | mrh |
| Matu Bible (Matu) | Matu, Chin | hlt |
| Lai Siengthou (Zbi) | Zo, Zou, Chin | zom |
| Zo Bible (Zbm) | Zo, Zou, Chin | zom |
| Pathen Thutheng BU (Thadou) | Thadou, Kuki, Chin | tcz |
| သမ္မာကျမ်း (ယုဒသန်) | Myanmar | mya |
| သမ္မာကျမ်း (မြန်​​​မာ့​​​စံ​​​မီ​​​) | Myanmar | mya |
| သမ္မာကျမ်း (ခေတ်သုံး) | Myanmar | mya |
| ကမ္ဘာသစ်ဘာသာပြန်ကျမ်း (နေ့စဉ်သုံး) | Myanmar | mya |
| Jinghpaw Common Language (JCLB) | Jinghpaw, Kachin | kac |
| Jinghpaw Hanson Version Bible (JHVB) | Jinghpaw, Kachin | kac |
| New International Version (NIV) | English | eng |
| King James Version (KJV) | English | eng |
| Bible in Basic English (BBE) | English | eng |
| World English Bible (WEB) | English | eng |
| American Standard Version (ASV) | English | eng |
| Berean Standard Bible (BSB) | English | eng |
| Contemporary English Version (CEV) | English | eng |
| Common English Bible (CEB) | English | eng |
| Contemporary English Version Interconfessional Edition (CEVDCI) | English | eng |
| Contemporary English Version (Anglicised) (CEVUK) | English | eng |
| Complete Jewish Bible (CJB) | English | eng |
| Catholic Public Domain Version (CJB) | English | eng |
| Christian Standard Bible (CSB) | English | eng |
| Plain English Version (Aboriginal) (PEV) | English | eng |
| Darby's Translation (DARBY) | English | eng |
| EasyEnglish Bible (EASY) | English | eng |
| English Standard Version (EASY) | English | eng |
| Holman Christian Standard Bible (HCSB) | English | eng |
| Good News Bible (Anglicised) (GNBDC) | English | eng |
| Good News Translation (GNT) | English | eng |
| Lexham English Bible (LEB) | English | eng |
| Det Danske Bibel (Danske) | Danish | dan |
| Det Norsk Bibelselskap 1930 (Norske) | Norwegian/Bokmål | nob |
| Norsk Bibel (Norske) | Norwegian/Bokmål | nob |
| Swedish Contemporary Bible (Swedish) | Swedish | swe |
| Kirkkoraamattu 1933/38 (Finnish) | Finnish | fin |
| La Bible Ostervald (French) | French | fra |
| Luther Bible (German) | German | deu |
| リビングバイブル (jcb) | Japanese | jpn |
| Colloquial Japanese (JACJ) | Japanese | jpn |
| Thai KJV (KJV) | Thai | tha |
| पवित्र बाइबिल OV (HINOVBSI) | Hindi | hin |
| सरल हिन्दी बाइबल (HCV) | Hindi | hin |
| 현대인의 성경 (KLB) | Korean | kor |
| 개역한글 (KRV) | Korean | kor |
| 当代译本 (CCB) | Chinese (Simplified) | zho |
| 新译本（简体字版） (CNVS) | Chinese (Simplified) | zho |
| Tagalog Contemporary Bible (ASND) | Tagalog | tgl |
> Books: 56 langs: 25

## task

- taskIdentify: `task`, `bible`,
- taskName: `wbc`,
- taskOption: `request`, `read`, `scan`,

```shell
node run {taskIdentify} {taskName} {taskOption}
node run task wbc
node run bible search
node run bible info
```

## taskName: `wbc`

```shell
# testing
node run task wbc request
node run task wbc read
node run task wbc check

# new
node run task wbc new

# lang: generate
node run task lang generate

# scan: update its context and content
node run task wbc scan

node run test wbc io
```

## translate

```shell
Bible
Book
Chapter
Verse

Old Testament
New Testament

0
1
2
3
4
5
6
7
8
9
```
