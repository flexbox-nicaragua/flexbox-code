// Copyright 2016 The Flexbox Authors. All rights reserved. 
// Licensed under the open source MIT License, which is in the LICENSE file. 
function readyToDump() {
    insertAllDump("twilioStatuses", ['datetime','hostname','energy',
                                            'start_range','end_range','current_%',
                                            'last_%','cost','text_count',
                                            'last_received','last_sent_kwh',
                                            'last_sent_percent']);
}



function addColnamesFromRow(row, element) {
    var header = "<thead><tr>"
    $.each(row, function(i, value) {
            header += "<th>" + i + "</th>\n";
    })
    header += "</tr>\n</thead>\n";
    element.append(header);
}
function addColnames(element, cols) {
    var header = "<thead><tr>"
    $.each(cols, function(i, value) {
            header += "<th>" + value + "</th>\n";
    })
    header += "</tr>\n</thead>\n";
    element.append(header);
}
function initTable(endpoint) {
    $("#" + endpoint).append("<div class=\"table-responsive\"> \n<table class=\"table table-bordered table-condensed\"> \n</div> \n</table>");
}

function insertAllDump(endpoint, cols) {
    $("#" + endpoint).append("<h4>" + endpoint + "</h4>");
    
    initTable(endpoint);
    addColnames($("#" + endpoint + " table"), cols);
    $.getJSON(endpoint, function(json) {
        sortJsonArrayByProperty(json.flexboxes,"last_record");
        $.each(json.flexboxes,function(index,data){
            $("#" + endpoint + " table").append("<tbody id=" + endpoint + "body" + "/> </tbody>")
            var otherCols = "";
            $.each(cols, function(key, value) {
                if(cols.indexOf(value) != -1) {
                    if(value === "datetime") {
                        dateCol = "<td>" + sprintf("%s", data.result[0][value]) + "</td>\n";
                    } else if(value === "hostname"||value === "last_received"||
                        value === "last_sent_percent"||value==="last_sent_kwh"){
                        otherCols += "<td>" + sprintf("%s", data.result[0][value]) + "</td>\n";
                    } else if(value === "current_%"||value === "last_%"){
                        otherCols += "<td>" + sprintf("%.5s", data.result[0][value]) + "</td>\n";
                    }
                    else {
                        otherCols += "<td>" + sprintf("%.7s", data.result[0][value]) + "</td>\n";
                    }
                }
            });
            if(data.status === "ERROR"){
                var row = "<tr class='text-danger bg-danger'>"+dateCol+otherCols;
            }
            else{
                var row = "<tr class='bg-success'>"+dateCol+otherCols;
            }
            row += "</tr>\n";
            $("#" + endpoint + "body").append(row);
        });
        
    });
}


function sortJsonArrayByProperty(objArray, prop, direction){
    if (arguments.length<2) throw new Error("sortJsonArrayByProp requires 2 arguments");
    var direct = arguments.length>2 ? arguments[2] : 1; //Default to ascending

    if (objArray && objArray.constructor===Array){
        var propPath = (prop.constructor===Array) ? prop : prop.split(".");
        objArray.sort(function(a,b){
            if (a[prop] && b[prop]){
                a = a[prop];
                b = b[prop];
            }
                        // convert numeric strings to integers
            //a = a.match(/^\d+$/) ? +a : a;
            //b = b.match(/^\d+$/) ? +b : b;
            return ( (a < b) ? -1*direct : ((a > b) ? 1*direct : 0) );
        });
    }
}
