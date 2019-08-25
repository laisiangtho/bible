const path = require('path');
const fs = require('fs-extra');
const xml2js = require('xml2js');
var param={};

var xmlParser = new xml2js.Parser({
  mergeAttrs: true,
  charkey:'text',
  explicitArray:false,
  explicitRoot:false,
  explicitCharkey:true
  // tagNameProcessors: [tagNameProcessors],
  // attrNameProcessors: [attrNameProcessors],
  // valueProcessors: [valueProcessors],
  // attrValueProcessors: [attrValueProcessors ]
});

function readXML(){
  return new Promise(function(resolve, reject) {
    // if (!param.bookIdentify) return reject(`...\x1b[35m${param.bookIdentify}\x1b[0m!`);
    if (!param.bookIdentify) return reject(param.msg.identify(param.bookIdentify));
    var filename = '*.xml'.replace('*',param.bookIdentify);
    fs.readFile(path.resolve(param.root,param.job.name,filename), function(e, data) {
      if (e) {
        if (e.code == 'ENOENT') {
          return reject(param.msg.fileNotExist(filename));
        }
        reject(e);
      } else {
        xmlParser.parseString(data, function (e, result) {
          if (e) return reject(e);
          resolve(parseStructure(result));
        });
      }
    });
  })
};

function writeJSON(data) {
  return new Promise((resolve, reject) => {
    var filename = param.json.file.name.replace('*',param.bookIdentify);
    param.json.write(path.resolve(param.root,'xml',filename),param.json.stringify(data,param.job.indentation)).then(function(){
      param.msg.log(param.msg.fileUpdatedFinal(filename));
      data.task=['xml'];
      resolve(data);
    },function(error){
      reject(error);
    });
  });
};

function parseStructure(data) {
  var result={
    info:parseInfo(data.info),
    note:{},
    digit:parseDigitName(data.digit),
    language:parseLanguage(data.language),
    testament:parseTestamentName(data.testament),
    story:parseStory(data.book),
    book:parseBookEach(data.book)
  };
  return result;
};

function parseInfo(data){
  var result={};
  for (var row of data) {
    if (row.hasOwnProperty('id') && row.hasOwnProperty('text')){
      if (Object.keys(row).length > 2){
        result[row.id]=row;
        delete row.id;
      } else {
        result[row.id]=row.text;
      }
    }
  }
  return result;
};

function parseDigitName(data){
  if (data) {
    var result=[];
    for (var digit of data) {
      result.push(digit.text)
    }
    return result;
  }
  return ["0","1","2","3","4","5","6","7","8","9"];
};

function parseLanguage(data){
  var result={};
  if (data) {
    for (var row of data) {
      if (row.hasOwnProperty('id') && row.hasOwnProperty('text')){
        result[row.id]=row.text;
      }
    }
  }
  return result;
};

function parseTestamentName(data){
  var result={};
  for (var testament of data) {
    result[testament.id]={};
    if (testament.hasOwnProperty('text')){
      testament.desc = testament.text;
      delete testament.text;
    }
    result[testament.id].info=testament;
    result[testament.id].other={};
    delete testament.id;
  }
  return result;
};

function parseStory(data){
  var result={};
  for (var book of data) {
    if (book.content){
      for (var row of book.content) {
        if (row.hasOwnProperty('ref') && row.hasOwnProperty('text')){
          if (!result.hasOwnProperty(book.id)){
            result[book.id]={}
          }
          var tmp = row.ref.split(',')[0].split('.'), chapter = tmp[1], verse = tmp[2];

          if (!result[book.id].hasOwnProperty(chapter)){
            result[book.id][chapter]={};
          }
          result[book.id][chapter][verse]=row;
        }
      }
    }
  }
  return result;
};

function parseBookEach(data){
  var result={};
  for (var book of data) {
    result[book.id]={
      info:{
        name:book.name,
        shortname:book.shortname,
        abbr:[],
        desc: ''
      },
      topic:{}
    };
    if (book.hasOwnProperty('info') && book.info.hasOwnProperty('text')) {
      result[book.id].info.desc=book.info.text;
    }
    result[book.id].chapter=parseBookChapter(book,book.id);
  }
  return result;
};

function parseBookChapter(book,bId){
  var result={};
  if (book.chapter.hasOwnProperty('verse')){
    result[book.chapter.id]={};
    result[book.chapter.id].verse=parseBookChapterVerse(book.chapter.verse,bId,book.chapter.id);
  } else{
    for (const chapter of book.chapter) {
      result[chapter.id]={};
      result[chapter.id].verse=parseBookChapterVerse(chapter.verse,bId,chapter.id);
    }
  }
  return result;
};

function parseBookChapterVerse(data,bId,cId){
  // NOTE expected text, id, merge, title, ref
  // NOTE bid cid, vid, text, title, ref, merge
  /*
  “ String ”
  */
  // var quoteStart = /“/g, quoteEnd = /”/;
  // var quoteFind = /"/g;
  try{
    var result={};
    for (const verse of data) {
      if (verse.text){

        // var mms = verse.text.match(/"(.*?)"/);
        // var quotes = verse.text.match(/'/g);
        // 'aadf aa "a3"'.replace(/"(.*)"/g,"“$1”")
        // 'aa"df" aa "a3"'.replace(/"(.*?)"/g,'“$1”')
        // /"/.test(verse.text)
        // var quotes = verse.text.match(/"/g);
        // if (quotes){
        //   verse.text = verse.text.replace(/"(.*?)"/g,"“$1”");
        //   if ((quotes.length % 2)){
        //     if (quotes.length>1) console.log('... Unclosed quotes:',bId,cId,verse.id,quotes.length)
        //   }
        // }
        result[verse.id]=verse;
        delete verse.id;
      } else {
        console.log('... no verse:',bId,cId,verse.id);
      }
    }
    return result;
  } catch(e){
    console.log('... Please check at book',bId,'chapter',cId);
    console.log(e);
    process.exit(1);
  }
};

module.exports = {
  main: async function(usr) {
    param = usr;

    try {
      const result = await readXML();
      try {
        const data = await writeJSON(result);
        return Promise.resolve();
      }
      catch (e) {
        return Promise.reject(e);
      }
    }
    catch (error) {
      return Promise.reject(error);
    }
  }
}