const path = require('path'), fs = require('fs'), xml2js = require('xml2js');
// const fs = require('fs-extra'), xml2js = require('xml2js');
var args = process.argv.slice(2);
// args.unshift('tmp');

// HACK: node lang/json {1/2/3} {option}

var xmlParser = new xml2js.Parser({
  mergeAttrs: true,
  charkey:'desc',
  explicitArray:false,
  explicitRoot:false,
  explicitCharkey:true
  // tagNameProcessors: [tagNameProcessors],
  // attrNameProcessors: [attrNameProcessors],
  // valueProcessors: [valueProcessors],
  // attrValueProcessors: [attrValueProcessors ]
}),
bookId = args[0],
currentDirectory = path.dirname(require.main.filename),
// currentPath = process.cwd(),
bookCollectionJSON = path.resolve(currentDirectory,'book.json'),
bookSource= path.resolve(currentDirectory,'*.xml'),
bookTarget = path.resolve(currentDirectory,'*.json'),
xmlRead = function(){
  return new Promise(function(resolve, reject) {
    fs.readFile(bookSource.replace('*',bookId), function(e, data) {
      if (e) return reject(e);
      xmlParser.parseString(data, function (e, result) {
        if (e) return reject(e);
        var result_custom = customStructure(result);
        fs.writeFile(bookTarget.replace('*',bookId), JSON_stringify(result_custom),function(e,r){
          if (e) {
            reject(e);
          } else {
            resolve(result_custom);
          }
        });
      });
    });
  })
},
JSON_stringify = function(data) {
  if (args.length > 1) {
    return JSON.stringify(data, null, 2);
  } else {
    return JSON.stringify(data);
  }
},
customStructure = function(data) {
  var result={};
  result.info = info(data.info);
  result.author = info(data.author);
  result.modification = data.modification;
  result.testament = testament(data.testament);
  result.book = testament(data.book);
  result.section = data.section.row;
  result.category = category(data.category);
  return result;
},
info = function(data){
  var result={};
  for (var row of data.row) {
    result[row.id]=row.desc;
  }
  return result;
},
testament = function(data){
  var result={};
  for (var row of data.row) {
    row.name=row.desc;
    result[row.id]=row;
    delete row.id;
    delete row.desc;
  }
  return result;
},
category = function(data){
  var result={};
  for (var rows of data) {
    result[rows.id]=rows.row;
  }
  return result;
};

new Promise(function(resolve, reject) {
  try {
    var tmp=fs.readFileSync(bookCollectionJSON).toString();
    resolve(JSON.parse(tmp));
  } catch (e) {
    resolve({})
  }
}).then(function(books){
  xmlRead().then(function(result){
    books[bookId]=result.info;
    fs.writeFile(bookCollectionJSON, JSON.stringify(books, null, 2),function(e,r){
      if (e) {
        console.log(e);
      } else {
        console.log(result.info);
      }
    });

  },function(e){
    console.log(e);
  })
},function(e){
  console.log(e)
});

// const xmlURL = 'https://raw.githubusercontent.com/scriptive/eba/master/lang/1.xml';

/*
private xmlToJson(xml: string): any {
    let doc = XmlObjects.parse(xml);
    var rootElement = doc.root;
    var result:any = {};
    var categoryElements = rootElement.elements('category');
    result.category={};
    for (var i = 0; i < categoryElements.length; i++) {
        var ae = categoryElements[i];
        var Id = ae.attribute('id').value;
        result.category[Id]={};
        var row = ae.elements('row');
        for (var r = 0; r < row.length; r++) {
          var cat = row[r];
          result.category[Id].book= cat.attribute('book').value;
          result.category[Id].chapter = cat.attribute('chapter').value;
          result.category[Id].verse = cat.attribute('verse').value;
          result.category[Id].tag = cat.attribute('tag').value;
          result.category[Id].text = cat.value;
        }
    }
    result.section={};
    var sectionElements = rootElement.elements('section')[0].elements('row');
    for (var i = 0; i < sectionElements.length; i++) {
      var ae = sectionElements[i];
      var Id = ae.attribute('id').value;
      result.section[Id]={};
      result.section[Id].name = ae.attribute('name').value;
      result.section[Id].group = ae.attribute('group').value;
      result.section[Id].text=ae.value;
    }
    result.book={};
    var bookElements = rootElement.elements('book')[0].elements('row');
    for (var i = 0; i < bookElements.length; i++) {
      var ae = bookElements[i];
      var Id = ae.attribute('id').value;
      result.book[Id]=ae.value;
    }
    result.testament={};
    var testamentElements = rootElement.elements('testament')[0].elements('row');
    for (var i = 0; i < testamentElements.length; i++) {
      var ae = testamentElements[i];
      var Id = ae.attribute('id').value;
      result.testament[Id]={};
      result.testament[Id].shortname=ae.attribute('shortname').value;
      result.testament[Id].text=ae.value;
    }
    result.info={};
    var infoElements = rootElement.elements('info')[0].elements('row');
    for (var i = 0; i < infoElements.length; i++) {
      var ae = infoElements[i];
      var Id = ae.attribute('id').value;
      result.info[Id]=ae.value;
    }
    result.author={};
    var authorElements = rootElement.elements('author')[0].elements('row');
    for (var i = 0; i < authorElements.length; i++) {
      var ae = authorElements[i];
      var Id = ae.attribute('id').value;
      result.author[Id]=ae.value;
    }
    return result;
}
*/