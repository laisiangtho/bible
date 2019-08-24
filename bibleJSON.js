const fs = require('fs-extra');

module.exports = {
  file:{
    book: './book.json',
    name:'*.json'
  },
  structure: function(){
    return {
      info: {
        identify: '',
        name: '',
        shortname: '',
        year: '',
        language: {
          text: '',
          textdirection: "ltr",
          name: ''
        },
        version: 1,
        description: '',
        publisher: '',
        contributors: '',
        copyright: ''
      },
      note:{
      },
      language:{
        book:"Book",
        chapter:"Chapter",
        verse:"Verse"
      },
      digit:["0","1","2","3","4","5","6","7","8","9"],
      testament:{
        1: {
          info: {
            name: "Old Testament",
            shortname: "OT",
            desc: ""
          }
        },
        2: {
          info: {
            name: "New Testament",
            shortname: "NT",
            desc: ""
          }
        }
      },
      story: {
      },
      book: {
      }
    };
  },
  exists: function(filename){
    return new Promise((resolve, reject) => {
      fs.exists(filename, function(e) {
        if (e) {
          resolve();
        } else {
          reject();
        }
      });
    });
  },
  read: function(filename){
    return new Promise((resolve, reject) => {
      try {
        const o = fs.readFileSync(filename).toString();
        resolve(JSON.parse(o));
      } catch (error) {
        reject(error)
      }
    });
  },
  // read: function(filename){
  //   return new Promise((resolve, reject) => {
  //     fs.exists(filename, function(e) {
  //       if (e) {
  //         try {
  //           var o=fs.readFileSync(filename).toString();
  //           resolve(JSON.parse(o));
  //         } catch (error) {
  //           reject(error)
  //         }
  //       } else {
  //         reject(usr.msg.fileNotExist(filename));
  //       }
  //     });
  //   });
  // },
  write: function(filename,data){
    return new Promise((resolve, reject) => {
      fs.writeFile(filename, data,'utf8',function(error){
        if (error) {
          reject(error);
        } else {
          resolve();
        }
      });
    });
  },
  stringify: function(data,indentation) {
    if (indentation) {
      return JSON.stringify(data, null, 2);
    } else {
      return JSON.stringify(data);
    }
  }
}