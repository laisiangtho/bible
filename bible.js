var path = require('path'), fs = require('fs-extra');
var args = process.argv.slice(2), taskIdentify=args[0], taskName=args[1], taskOption=args[2];
// args.unshift('tmp');
// currentPath = process.cwd();

var rootDirectory = path.dirname(require.main.filename),
bibleCollection={},
bibleCollectionJSON = path.resolve(rootDirectory,'book.json'),
settings={
  args: args,
  bookIdentify: null,
  rootDirectory: rootDirectory,
  taskIdentify: taskIdentify,
  task:{
    ph4:{
      dirname:'ph4',
      target:'json',
      extension:'*.SQLite3'
    },
    koh:{
      dirname:'koh',
      target:'json',
      extension:'*.json'
    },
    wbc:{
      dirname:'wbc',
      target:'json',
      extension:'*.json'
    },
    sqlite:{
      dirname:'sqlite',
      final:true,
      extension:'*.db'
    },
    json:{
      dirname:'json',
      target:'sqlite',
      extension:'*.json'
    },
    xml:{
      dirname:'xml',
      target:'json',
      extension:'*.xml'
    }
  },
  message:{
    book: function(bId,cId){
      var spaces = (bId < 10)?' ':'';
      process.stdout.write(`\n....\x1b[2mBook\x1b[8m:\x1b[35m${spaces}${bId}\x1b[0m > \x1b[2mchapter\x1b[8m:`);
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
    }
  }
},
bibleCollectionRead = function(){
  return new Promise(function(resolve, reject) {
    try {
      var tmp = fs.readFileSync(bibleCollectionJSON).toString();
      bibleCollection = JSON.parse(tmp);
      resolve();
    } catch (e) {
      reject(`...no\x1b[35m book collection\x1b[0m provided?`);
    }
  })
},
bibleCollectionWrite = function(result,callback){
  var tmp = path.basename(bibleCollectionJSON);
  // var resultProcess=['xml','json','sqlite'];
  if (result instanceof Object && result.info){
    bibleCollection.updated = new Date();
    bibleCollection.version++;
    if (result.task){
      if (!bibleCollection.hasOwnProperty('collection'))bibleCollection.collection={};
      for (const resultTaskId of result.task) {
        if (!bibleCollection.collection.hasOwnProperty(resultTaskId)){
          bibleCollection.collection[resultTaskId]=[];
        }
        if (bibleCollection.collection[resultTaskId].indexOf(settings.bookIdentify) < 0){
          bibleCollection.collection[resultTaskId].push(settings.bookIdentify);
        }
      }
    }
    var bookIndex = bibleCollection.book.findIndex((x)=>x.identify==settings.bookIdentify);
    if (bookIndex >= 0) {
      bibleCollection.book[bookIndex]=result.info;
    } else {
      bibleCollection.book.push(result.info)
    }
    fs.writeFile(bibleCollectionJSON, JSON.stringify(bibleCollection, null, 2),function(e){
      if (e) {
        callback(e);
      } else {
        callback(`...updated\x1b[32m ${tmp}\x1b[0m`);
      }
    });
  } else {
    callback(`...skip updating\x1b[35m ${tmp}\x1b[0m`);
  }
},
task=null,
taskList=[],
taskFilter={
  fill:function(){
    // NOTE: items that are not available in target collection will be push to task list!
    // taskActive, taskName taskFinal taskTarget taskExtension
    if (bibleCollection.collection.hasOwnProperty(taskIdentify) && settings.task.hasOwnProperty(taskIdentify)) {
      var taskTarget = settings.task[taskIdentify].target;
      if (bibleCollection.collection.hasOwnProperty(taskTarget)) {
        var src = bibleCollection.collection[taskIdentify], tar = bibleCollection.collection[taskTarget];
        var response = src.filter(e => (tar.indexOf(e) === -1)).filter(Boolean);
        console.log(`\n..To fill:\x1b[35m ${src.length}/${response.length}\x1b[0m`);
        return response;
      }
    }
  },
  todo:function(o){
    // NOTE: list of items that needed to get done!
    console.log(`\n..Todo`);
    if (bibleCollection.collection.hasOwnProperty(taskIdentify)){
      var tar = bibleCollection.collection[taskIdentify], src=[];
      if (o) {
        src = o.split(',').map(e => e.trim()).filter(Boolean);
      } else {
        // REVIEW: remove -> dictionary,crossreferences,commentaries
        fs.readdirSync(path.resolve(rootDirectory,settings.task[taskIdentify].dirname)).forEach(file => {
          if (/dictionary|crossreferences|commentaries|README/.test(file) == false){
            var taskExtension = settings.task[taskIdentify].extension.replace('*','');
            src.push(file.replace(taskExtension,''));
          }
        })
      }
      var todo = src.filter(e => (tar.indexOf(e) === -1)).filter(Boolean);

      console.log(`  ${taskIdentify.toUpperCase()}:\x1b[35m ${tar.length}\x1b[0m`);
      console.log(`  Items/Todo:\x1b[35m ${src.length}/${todo.length}\x1b[0m`);

      if (todo.length) {
        // console.log(`  todo:\x1b[35m ${todo.join(',')}\x1b[0m`);
        console.log(`\n..Next?\n  \x1b[31mnode \x1b[32mbible \x1b[36m${taskIdentify} \x1b[33mlist:\x1b[35m${todo.join(',')} \x1b[31mtrue\x1b[0m`);
      }

      var todoTarget = settings.task[taskIdentify].target;
      var dest = bibleCollection.collection[todoTarget]
      var todoDest = src.filter(e => (dest.indexOf(e) === -1)).filter(Boolean);
      if (todoDest.length){
        var taskIdentifyTarget = (settings.task[todoTarget].hasOwnProperty('final'))?taskIdentify:todoTarget;
        console.log(`\n..Target?:\x1b[35m ${todoDest.length}\x1b[0m\n  \x1b[31mnode \x1b[32mbible \x1b[36m${taskIdentifyTarget} \x1b[33mlist:\x1b[35m${todoDest.join(',')} \x1b[0m`);
      }
    }
    return [];
  },
  all:function(){
    // NOTE: all
    if (bibleCollection.collection.hasOwnProperty(taskIdentify)){
      return JSON.parse(JSON.stringify(bibleCollection.collection[taskIdentify]));
    }
  },
  list:function(o){
    // NOTE: list with comma seperated && /\,/.test(o)
    return o.split(',').map(e => e.trim()).filter(Boolean);
  }
},
taskValidate=function(){
  var f0 = args[1], taskMulti = /:/.test(f0);
  taskList=[f0];
  if (taskMulti) {
    var f1 = f0.split(':');
    if (taskFilter.hasOwnProperty(f1[0])){
      taskList = taskFilter[f1[0]](f1[1]);
    }
  } else if (taskFilter.hasOwnProperty(f0)){
    taskList = taskFilter[f0]();
  }
},
taskModule=function(){
  return new Promise(function(resolve, reject) {
    try{
      task = require('./0'.replace(0,taskIdentify));
      resolve()
    } catch(e){
      reject(e);
    }
  })
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
  settings.bibleCollection = bibleCollection;
  if (settings.bookIdentify) {
    console.log(`\n..bookIdentify: "\x1b[36m${settings.bookIdentify}\x1b[0m"`)
  } else {
    console.log(`\n..bookIdentify: `)
  }

  return task.main(settings).then(function(response){
    bibleCollectionWrite(response,(e)=>{
      console.log(e);
      taskInitiate();
    });
  },function(e){
    console.log(e);
    taskInitiate();
  });
};

bibleCollectionRead().then(function(){
  taskModule().then(function(){
    taskValidate();
    taskInitiate();
  },function(){
    settings.message.unknown(taskIdentify);
  })
},function(e){
  console.log(e);
});