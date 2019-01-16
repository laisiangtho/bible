var path = require('path');
var fs = require('fs-extra');
var args = process.argv.slice(2);
var taskIdentify=args[0];
// args.unshift('tmp');
/**
 * NOTE: node bible {filename:1/2/3} {option:sqlite,json} {true}
 * if option is json then there is thrid argument JSON.stringify would format
 * node bible json/ph4/xml identify
 * xml: xml->json
 * json: json->sqlite
 * scan: ?->json
 * sqlite: ?
 *  */
try{
  var task = require('./0'.replace(0,taskIdentify));
} catch(e){
  console.log(`\n ...\x1b[31m${taskIdentify}\x1b[0m?`)
  process.exit(1);
}
var currentDirectory = path.dirname(require.main.filename),
currentPath = process.cwd(),
bookCollection={},
bookCollectionJSON= path.resolve(currentDirectory,'book.json'),
activeDirectory={
  ph4:{
    name:'ph4',
    target:'json',
    extension:'*.SQLite3'
  },
  sqlite:{
    name:'sqlite',
    final:true,
    extension:'*.db'
  },
  json:{
    name:'json',
    target:'sqlite',
    extension:'*.json'
  },
  xml:{
    name:'xml',
    target:'json',
    extension:'*.xml'
  }
},
settings={
  args: args,
  bookIdentify: '',
  currentDirectory: currentDirectory,
  bookSourceXML: path.resolve(currentDirectory,activeDirectory.xml.name,activeDirectory.xml.extension),
  bookSourceJSON: path.resolve(currentDirectory,activeDirectory.json.name,activeDirectory.json.extension),
  // bookSourcePH4: path.resolve(currentDirectory,'ph4','*.SQLite3'),
  bookSourcePH4: path.resolve(currentDirectory,activeDirectory.ph4.name,activeDirectory.ph4.extension),
  bookTargetSQLite: path.resolve(currentDirectory,activeDirectory.sqlite.name,activeDirectory.sqlite.extension),
  message:{
    book: function(bId,cId){
      var bTc = (bId < 10)?' ':'';
      process.stdout.write(`\n....\x1b[2mBook\x1b[8m:\x1b[35m${bTc}${bId}\x1b[0m > \x1b[2mchapter\x1b[8m:`);
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
    }
  }
},
bookCollectionUpdate = function(result,callback){
  var tmp = path.basename(bookCollectionJSON);
  // var resultProcess=['xml','json','sqlite'];
  if (result instanceof Object && result.info){
    bookCollection.updated = new Date();
    bookCollection.version++;
    if (result.task){
      if (!bookCollection.hasOwnProperty('collection'))bookCollection.collection={};
      for (const resultTaskId of result.task) {
        if (!bookCollection.collection.hasOwnProperty(resultTaskId)){
          bookCollection.collection[resultTaskId]=[];
        }
        if (bookCollection.collection[resultTaskId].indexOf(settings.bookIdentify) < 0){
          bookCollection.collection[resultTaskId].push(settings.bookIdentify);
        }
      }
    }
    var bookIndex = bookCollection.book.findIndex((x)=>x.identify==settings.bookIdentify);
    if (bookIndex >= 0) {
      bookCollection.book[bookIndex]=result.info;
    } else {
      bookCollection.book.push(result.info)
    }
    fs.writeFile(bookCollectionJSON, JSON.stringify(bookCollection, null, 2),function(e){
      if (e) {
        callback(e);
      } else {
        callback(`...updated\x1b[32m ${tmp}\x1b[0m`);
      }
    });
  } else {
    callback(`...skip writing\x1b[35m ${tmp}\x1b[0m`);
  }
},
taskList=[],
taskListFilter={
  fill:function(tasks){
    // NOTE: items that not available in target collection
    if (tasks && bookCollection.collection.hasOwnProperty(taskIdentify) && bookCollection.collection.hasOwnProperty(tasks)){
      // var src = bookCollection.collection.json, tar = bookCollection.collection.sqlite;
      var src = bookCollection.collection[taskIdentify], tar = bookCollection.collection[tasks];
      return src.filter(tS => (tar.indexOf(tS) === -1)).filter(Boolean);
    }
  },
  todo:function(tasks){
    console.log(`\n..Todo`);
    if (bookCollection.collection.hasOwnProperty(taskIdentify)){
      var tar = bookCollection.collection[taskIdentify], src=[];
      if (tasks) {
        src = tasks.split(',').map(e => e.trim()).filter(Boolean);
      } else {
        // dictionary crossreferences commentaries
        fs.readdirSync(path.resolve(currentDirectory,activeDirectory[taskIdentify].name)).forEach(file => {
          if (/dictionary|crossreferences|commentaries/.test(file) == false){
            var ext = activeDirectory[taskIdentify].extension.replace('*','');
            src.push(file.replace(ext,''));
          }
        })
      }

      // var tar = bookCollection.collection[taskIdentify], src = tasks.split(',').map(e => e.trim()).filter(Boolean);
      var todo = src.filter(e => (tar.indexOf(e) === -1)).filter(Boolean);

      console.log(`  ${taskIdentify.toUpperCase()}:\x1b[35m ${tar.length}\x1b[0m`);
      console.log(`  Check/Todo:\x1b[35m ${src.length}/${todo.length}\x1b[0m`);
      
      if (todo.length) {
        // console.log(`  todo:\x1b[35m ${todo.join(',')}\x1b[0m`);
        console.log(`\n..Next?`);
        console.log(`  \x1b[31mnode \x1b[32mbible \x1b[36m${taskIdentify} \x1b[33mlist:\x1b[35m${todo.join(',')} \x1b[31mtrue\x1b[0m`);
      } 

      var todoTarget = activeDirectory[taskIdentify].target;
      var dest = bookCollection.collection[todoTarget]
      var todoDest = src.filter(e => (dest.indexOf(e) === -1)).filter(Boolean);
      if (todoDest.length){

        var taskIdentifyTarget = (activeDirectory[todoTarget].hasOwnProperty('final'))?taskIdentify:todoTarget;

        console.log(`  Destination:\x1b[35m ${todoDest.length}\x1b[0m`);

        console.log(`\n..Next?`);
        console.log(`  \x1b[31mnode \x1b[32mbible \x1b[36m${taskIdentifyTarget} \x1b[33mlist:\x1b[35m${todoDest.join(',')} \x1b[0m`);
      }
    }
    return [];
  },
  all:function(tasks){
    // NOTE: all
    if (tasks && bookCollection.collection.hasOwnProperty(taskIdentify)){
      return bookCollection.collection[taskIdentify];
    }
  },
  list:function(tasks){
    // NOTE: list with comma seperated
    if (tasks && /\,/.test(tasks)){
      return tasks.split(',').map(e => e.trim()).filter(Boolean);
    }
  }
},
taskListValidate=function(){
  // node bible xml all:json 1
  // node bible json all:sqlite
  // node bible xml fill:json 1
  // node bible json fill:sqlite
  // node bible ph4 list:a,b,c,c
  var taskCurrent = args[1], taskMulti = /:/.test(taskCurrent);
  taskList=[taskCurrent];
  if (taskMulti) {
    var tmp = taskCurrent.split(':');
    if (taskListFilter.hasOwnProperty(tmp[0])){
      taskList = taskListFilter[tmp[0]](tmp[1]);
    }
  }
},

taskInitiate=function(){
  if (taskList.length){
    taskProcess(taskList.shift());
  } else {
    console.log(`\n..Finish!`);
  }
},
taskProcess=function(taskCurrent){
  settings.bookIdentify = taskCurrent;
  settings.bookCollection = bookCollection;
  console.log(`\n..bookIdentify:\x1b[36m ${settings.bookIdentify}\x1b[0m`)
  return task.main(settings).then(function(response){
    bookCollectionUpdate(response,(e) => {
      console.log(e);
      taskInitiate();
    });
  },function(e){
    console.log(e);
    taskInitiate();
  });
};

new Promise(function(resolve, reject) {
  try {
    var tmp = fs.readFileSync(bookCollectionJSON).toString();
    bookCollection = JSON.parse(tmp);
    resolve();
  } catch (e) {
    reject(`...no\x1b[35m book collection\x1b[0m provided?`);
  }
}).then(function(){
  taskListValidate();
  taskInitiate();
},function(e){
  console.log(e)
});