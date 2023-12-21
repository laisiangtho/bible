const path = require('path');
// const fs = require('fs-extra');

// var args = process.argv.slice(2), taskIdentify=args[0], taskName=args[1], taskOption=args[2];
// args.unshift('tmp');
// currentPath = process.cwd();

var usr = {
  books:{}
};
usr.msg = require('./bibleMsg');
usr.json = require('./bibleJSON');

usr.root = path.dirname(require.main.filename);
usr.job = require('minimist')(process.argv.slice(2));
/*
node bible wbc  bible/348/GEN.1.JCLB --indentation
node bible wbc --id=bible/348/GEN.1.JCLB --indentation
node bible --name=wbc --id=bible/348/GEN.1.JCLB --indentation
*/
if (usr.job._.length) {
  if (!usr.job.name) {
    usr.job.name = usr.job._[0];
  }
  if (!usr.job.id) {
    usr.job.id = usr.job._[1];
  }
}

usr.bookIdentify = usr.job.id;

async function bookRead(){
  try {
    await usr.json.exists(usr.json.file.book);
    try {
      usr.books = await usr.json.read(usr.json.file.book);
    } catch (error) {
      // NOTE: Unexpected string in JSON at position 9303
      // NOTE: Unexpected token { in JSON at position 9236
      // console.log(error);
      // var re = /(.*token\s+)(.*)(\s+in.*)/;
      // var newtext = error.message.replace(re, "$2");
      // console.log(newtext)

      return Promise.reject(error.message.replace('JSON',usr.msg.fileName(usr.json.file.book)));
    }
  } catch (error) {
    return Promise.reject(usr.msg.fileNotExist(usr.json.file.book));
  }
};

async function bookWrite(result){
  // var resultProcess=['xml','json','sqlite'];
  if (result instanceof Object && result.info){
    usr.books.updated = new Date();
    usr.books.version++;
    if (result.task){
      if (!usr.books.hasOwnProperty('collection'))usr.books.collection={};
      for (const resultTaskId of result.task) {
        if (!usr.books.collection.hasOwnProperty(resultTaskId)){
          usr.books.collection[resultTaskId]=[];
        }
        if (usr.books.collection[resultTaskId].indexOf(usr.job.id) < 0){
          usr.books.collection[resultTaskId].push(usr.job.id);
        }
      }
    }
    var bookIndex = usr.books.book.findIndex((x)=>x.identify==usr.job.id);
    if (bookIndex >= 0) {
      usr.books.book[bookIndex]=result.info;
    } else {
      usr.books.book.push(result.info)
    }
    try {
      await usr.json.write(usr.json.file.book, usr.json.stringify(usr.books, true));
      return usr.msg.fileUpdated(usr.json.file.book);
    } catch (error) {
      return error.message;
    }
  } else {
    return Promise.resolve(usr.msg.fileSkipUpdated(usr.json.file.book));
  }
};

function jobInitiate(){
  return new Promise(function(resolve, reject) {
    try{
      if (usr.job.name){
        const o = require(path.resolve(usr.root,usr.job.name));
        if (o.hasOwnProperty('main') && typeof o.main == 'function') {
          resolve(o);
        } else {
          reject(usr.msg.moduleNoMain(usr.job.name));
        }
      } else {
        reject(usr.msg.moduleNotProvided());
      }
    } catch(error){
      if (error.message.includes("Cannot find module")){
        reject(usr.msg.moduleNotFound(usr.job.name));
      } else {
        reject(error);
      }
    }
  })
};

bookRead().then(function(){
  jobInitiate().then(function(o){
    console.log(usr.msg.identify(usr.job.id));
    o.main(usr).then(function(response){
      bookWrite(response).then(function(s){
        // NOTE: book collection updated/skip updating...
        console.log(s);
      });
    },function(e){
      // NOTE: module rejected message...
      console.log(e);
    });
  },function(e){
    // NOTE: module not exists/syntax error in module...
    console.log(e);
  });
},function(e){
  // NOTE: book collection not exists, unable to parse json...
  console.log(e);
});
