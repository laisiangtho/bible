const path = require('path');
// const fs = require('fs-extra');
const request = require('request');
const htmlParser = require('node-html-parser');
// usr, param
var param = {};
var dataBookName=[];
var dataBibleJSON={};
var requestBookId = '';

// div.navLinkPrev a -> data-book data-chapter
// div.navLinkNext a -> data-book data-chapter
// select#Book option-value and context
// https://www.jw.org/my/စာပေများ/သမ္မာကျမ်းစာ/nwt/ကျမ်း/json/html/19105024-19105025
// https://www.jw.org/my/စာပေများ/သမ္မာကျမ်းစာ/nwt/ကျမ်း/ကမ္ဘာဦး/1/

// node bible jwb jwmynwt
// node bible json jwmynwt
// node bible jwb my/var --indentation
// node bible jwb my/စာပေများ/သမ္မာကျမ်းစာ/nwt/ကျမ်း/ကမ္ဘာဦး/1 --indentation
// node bible jwb /my/စာပေများ/သမ္မာကျမ်းစာ/nwt/ကျမ်း/ကမ္ဘာဦး/1 --indentation
// node bible jwb my/စာပေများ/သမ္မာကျမ်းစာ/nwt/ကျမ်း/ဗျာဒိတ်/22

function initial(){
  return new Promise(function(resolve, reject) {
    readLocalJSON().then(function(data){
      dataBibleJSON=data;
      if (param.apiData){
        asyncEach().then(function(e){
          resolve(e);
        },function(e){
          reject(e);
        });
      } else {
        // resolve(dataBibleJSON);
        parseFinalJSON(dataBibleJSON).then(function(e){
          resolve(e);
        },function(e){
          reject(e);
        });
      }
    },function(e){
      reject(e);
    });
  });
};

function asyncEach(){
  return new Promise(function(resolve, reject) {
    asyncTask(resolve, reject).then(function(e){
      resolve(e);
    },function(e){
      reject(e);
    });
  });
};

async function asyncTask(resolve, reject){
  try {
    await requestChapter();
    if (param.apiURLChapter) {
      return asyncEach();
    } else {
      resolve(dataBibleJSON);
    }
  }
  catch (e) {
    reject(e);
  }
};

function requestChapter() {
  return new Promise(function(resolve, reject) {
    request(param.apiURLChapter, { json: true }, async function(e, res, body) {
      if (e) {
        reject(e);
      } else {
        const root = htmlParser.parse(body);
        // const rootChapter = root.querySelector('div.chapter');
        // const currentBookChapter = rootChapter.attributes['data-usfm'].split('.');
        // var bookId = 1;
        // var bookShortName = currentBookChapter[0];
        // var chapterId = currentBookChapter[1];

        // var bookInfo = dataBookName.find(element => element.usfm === bookShortName);
        // var index = dataBookName.indexOf(bookInfo);
        // if (index > -1) {
        //   bookId =  index + bookId;
        // } else {
        //   return reject('No book info found');
        // }

        // NOTE next
        var hasNext = root.querySelector('div.navLinkNext a');
        param.apiURLChapter = null;
        if (hasNext) {
          if (param.apiDataOnlyOne == false){
            if (hasNext.attributes['data-book']) {
              param.apiURLChapter = param.apiDomain.replace('/*',hasNext.attributes.href);
            }
          }
        }

        // NOTE dataBookName
        if (dataBookName.length == 0) {
          var hasBook = root.querySelectorAll('#Book option');
          hasBook.forEach(function(h) {
            dataBookName.push({
              id:h.attributes.value,
              name:h.text
            });
          });
          // console.log(dataBookName)
        }

        var nameDump = root.querySelector('article');
        var bookName = nameDump.attributes['data-bookname'];
        var bookId = nameDump.attributes['data-booknum'];
        var chapterId = nameDump.attributes['data-chapter'];
        // console.log(bookName)
        // console.log(bookId)
        // console.log(chapterId)
        if (!bookId){
          return resolve();
        }

        if (!dataBibleJSON.book.hasOwnProperty(bookId)) {
          dataBibleJSON.book[bookId]={
            info:{
              name: bookName,
              shortname: '',
              abbr:[],
              desc: ""
            },
            topic:[],
            chapter:{}
          };
        }
        dataBibleJSON.book[bookId].chapter[chapterId]={
          verse:{}
        };

        if (requestBookId == bookId) {
          param.msg.chapter(chapterId);
        } else {
          param.msg.book(bookId,chapterId);
        }
        requestBookId = bookId;
        var verseStory =[];
        await root.querySelectorAll('div.BibleChapterOutline ul li').forEach(async function(v) {
          var makeup = function(node){
            var p = node.querySelector('p');
            var verseTitle = p.rawText;
            var verseFrom = null;
            var verseTo = null;
            var a = p.querySelector('a');
            if (a) {
              verseTitle = p.innerHTML.replace(/(<([^>]+)>)/g,'--').replace(/--(.*)--/g,' ').replace(/\(.?\)/,' ');
              // NOTE: 19139007 19-139-007
              var verseIdTmp =a.attributes['data-targetverses'].split('-');
              verseFrom = verseIdTmp[0].substring(5,8).replace(/^0+/, '');
              if (verseIdTmp.length == 2){
                verseTo = verseIdTmp[1].substring(5,8).replace(/^0+/, '');
              }
            }
            return {
              from: verseFrom,
              to: verseTo,
              text: verseTitle.replace(/\s\s+/g, ' ').trim()
            }
          }

          verseStory.push(makeup(v));
          await v.querySelectorAll('ul li').forEach(function(e){
            verseStory.push(makeup(e));
          });
        });
        // NOTE id="v38001001"
        // NOTE id="v1001002"
        await root.querySelectorAll('#bibleText span.verse').forEach(async function(v) {
          // var verseId = v.attributes.id.substring(5,8).replace(/^0+/, '');
          var verseId = v.attributes.id.substr(v.attributes.id.length - 3).replace(/^0+/, '');
          var verseContent = v.querySelectorAll('span').map(function(e){
            return e.innerHTML.replace(/(<([^>]+)>)/g,'--').replace(/--([*|+])--/g,' ');
          });

          // var verseTitle = await verseStory.filter(e=>e.from == verseId).some(e=>e.text);
          var verseTitle = await verseStory.filter(e=>e.from == verseId).map(e=>e.text);

          var verseText = await verseContent.map(e=>e.replace(/----(.*)----/,' ')).join(' ').replace(/\s\s+/g, ' ').trim();

          dataBibleJSON.book[bookId].chapter[chapterId].verse[verseId]={
            text:verseText,
            title:verseTitle.join(', '),
            ref:'',
            merge:''
          }
        })
        resolve();
      }
    });
  });
};

function readLocalJSON(){
  // return for dataBibleJSON
  return new Promise(function(resolve, reject) {
    if (!param.bookIdentify) return reject(param.msg.identify(param.bookIdentify));
    var filename = param.json.file.name.replace('*',param.bookIdentify);
    param.json.read(path.resolve(param.root,param.job.name,filename)).then(function(data){
      resolve(data);
    },function(error){
      if (error.code == 'ENOENT') {
        param.msg.log(param.msg.fileToBeCreated());
        resolve(param.json.structure());
      } else {
        reject(error);
      }
    })
  })
};

function writeJSON(data) {
  return new Promise((resolve, reject) => {
    if (param.apiData){
      writeLocalJSON(data).then(function(){
        resolve();
      },function(e){
        reject(e);
      });
    } else if (dataBibleJSON.info.identify && dataBibleJSON.info.name && dataBibleJSON.info.shortname && dataBibleJSON.info.year){
      writeFinalJSON(data).then(function(){
        data.task=['jwb'];
        resolve(data);
      },function(e){
        reject(e);
      });
    } else {
      param.msg.log(param.msg.infoMissing());
      if (typeof data === 'string'){
        param.msg.unknown(data);
      }
      resolve();
    }
  });
};

function writeLocalJSON(data) {
  return new Promise((resolve, reject) => {
    var filename = param.json.file.name.replace('*',param.bookIdentify);
    param.json.write(path.resolve(param.root,param.job.name,filename),param.json.stringify(data,param.job.indentation)).then(function(){
      param.msg.log(param.msg.fileUpdatedLocal(filename));
      resolve();
    },function(error){
      reject(error);
    });
  });
};

function writeFinalJSON(data) {
  return new Promise((resolve, reject) => {
    var filename = param.json.file.name.replace('*',param.bookIdentify);
    param.json.write(path.resolve(param.root,'json',filename),param.json.stringify(data,param.job.indentation)).then(function(){
      param.msg.log(param.msg.fileUpdatedFinal(filename));
      resolve();
    },function(error){
      reject(error);
    });
  });
};

function parseFinalJSON(data){
  return new Promise(function(resolve, reject) {
    try {
      var result={
        info:data.info,
        note:{},
        digit:data.digit,
        language:data.language,
        testament:data.testament,
        story:data.story,
        book:data.book
      };
      return resolve(result);
    } catch (e) {
      return reject(e);
    }
  });
};


module.exports = {
  main: function(usr) {
    param = usr;
    param.apiDomain = '*/gro.wj.www//:sptth'.split('').reverse().join('');
    param.apiDataOnlyOne=false;
    param.apiData = false;
    param.apiURLChapter = null;
    // param.apiURLBookName = null;

    if (/\//g.test(param.bookIdentify)){
      param.apiData = true;
      var tmp = param.bookIdentify.split('/');
      var bIdentify= tmp[0];
      var bType= tmp[3];

      if (!bIdentify) {
        // NOTE -> /my/စာပေများ/သမ္မာကျမ်းစာ/nwt/ကျမ်း/ကမ္ဘာဦး/1
        bIdentify = tmp[1];
        bType = tmp[4];
        param.apiDataOnlyOne = true;
        tmp.shift();
      } else {
        // NOTE -> my/စာပေများ/သမ္မာကျမ်းစာ/nwt/ကျမ်း/ကမ္ဘာဦး/1
      }
      param.bookIdentify = 'jw-*'.replace('-',bIdentify).replace('*',bType);
      param.apiURLChapter = encodeURI(param.apiDomain.replace('*',tmp.join('/')));
    }

    return new Promise(function(resolve, reject) {
      initial().then(function(result){
        writeJSON(result).then(function(r){
          resolve(r);
        },function(e){
          reject(e);
        });
      },function(e){
        reject(e);
      });
    });
  }
};