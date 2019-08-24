const path = require('path');

module.exports = {
  fileName: function(fileName){
    // Unexpected string in ./book.json at position 9303
    return '\x1b[31mfile\x1b[0m'.replace('file',path.basename(fileName));
  },
  fileUpdated: function(fileName){
    return '...updated\u001B[32m file\u001B[0m'.replace('file',path.basename(fileName));
  },
  fileSkipUpdated: function(fileName){
    return '..skip updating\x1b[35m file\x1b[0m'.replace('file',path.basename(fileName));
  },
  fileNotExist: function(fileName){
    return '...\x1b[31mfile \x1b[35mdoes not\x1b[0m exist!'.replace('file',path.basename(fileName));
  },
  fileToBeCreated: function(file){
    return 'new \x1b[35mJSON\x1b[0m to be created!'.replace('JSON',file||'JSON');
  },
  fileUpdatedLocal: function(fileName){
    return '\n...updated local\x1b[32m file\x1b[0m!'.replace('file',path.basename(fileName));
  },
  fileUpdatedFinal: function(fileName){
    return '\n...updated final\x1b[32m file\x1b[0m!'.replace('file',path.basename(fileName));
  },
  moduleNoMain: function(mod){
    return '...\x1b[31mmodule \x1b[0mhas no \x1b[35mmain\x1b[0m function!'.replace('module',mod);
  },
  moduleNotProvided: function(){
    return '...\x1b[31mmodule \x1b[0mnot \x1b[35mprovided\x1b[0m!';
  },
  moduleNotFound: function(mod){
    return '...\x1b[31mmodule \x1b[0mnot found!'.replace('module',mod);
  },
  identify: function(name){
    return '\n..identify: "\x1b[36mname\x1b[0m"'.replace('name',name || '?');
  },
  infoMissing: function(){
    // Required: info > identify,name,shortname,year for final output!
    return '\n...\x1b[31info\x1b[0m > \x1b[36midentify\x1b[0m, \x1b[36mname\x1b[0m, \x1b[36mshortname\x1b[0m, \x1b[36myear\x1b[0m for final output!';
  },
  book: function(bId,cId,bookName,chapterName){
    // var spaces = (bId < 10)?' ':'';
    bookName = bookName?bookName:'Book';
    chapterName = chapterName?chapterName:'chapter';
    process.stdout.write(`\n....\x1b[2m${bookName}\x1b[8m \x1b[35m${bId}\x1b[0m > \x1b[2m${chapterName}\x1b[0m:`);
    if (cId){
      if (cId instanceof Array){
        this.chapter(cId.join(' '));
      } else {
        this.chapter(cId);
      }
    }
  },
  chapter: function(cId){
    process.stdout.write(` \x1b[33m${cId}\x1b[0m`);
  },
  unknown: function(item){
    console.log(`\n...\x1b[31m${item}\x1b[0m?`);
  },
  standard: function(item){
    console.log(`\n...\x1b[31m${item}\x1b[0m`);
  },
  log: function(item){
    console.log(item);
  }
}