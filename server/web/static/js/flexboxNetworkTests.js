// Copyright 2016 The Flexbox Authors. All rights reserved. 
// Licensed under the open source MIT License, which is in the LICENSE file. 
function readyToDump() {
    insertAllDump("networkTests", ['datetime','hostname','parm','seqn','ts','fail_pcnt','max','avg']);
    /*
    insertDump("flxbxD1", ['datetime','parm','hostname','seqn','ts','fail_pcnt','max','avg']);
    insertDump("flxbxD17", ['datetime','parm','hostname','seqn','ts','fail_pcnt','max','avg']);
    insertDump("flxbxD24", ['datetime','parm','hostname','seqn','ts','fail_pcnt','max','avg']);
    insertDump("flxbxD26", ['datetime','parm','hostname','seqn','ts','fail_pcnt','max','avg']);
    insertDump("flxbxD28", ['datetime','parm','hostname','seqn','ts','fail_pcnt','max','avg']);
    */
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
function insertDump(endpoint, cols) {
    //sp = $("#" + endpoint).add("</span>");
    //sp.addClass("warning");
    $("#" + endpoint).append("<h4>" + endpoint + "</h4>");
    
    initTable(endpoint);
    $.getJSON(endpoint, function(data) {
        if(data.status === "ERROR") {
            $("#" + endpoint + " h4").addClass("text-danger").addClass("bg-danger");
        } else {
            $("#" + endpoint + " h4").addClass("bg-success");
        }
        addColnames($("#" + endpoint + " table"), cols);
        $("#" + endpoint + " table").append("<tbody id=" + endpoint + "body" + "/> </tbody>")
        $.each(data.result, function(i, rowValue) {
            var otherCols = "";
            $.each(cols, function(key, value) {
                if(cols.indexOf(value) != -1) {
                    if(value === "datetime") {
                        dateCol = "<td>" + sprintf("%s", rowValue[value]) + "</td>\n";
                    } else if(value === "hostname"){
                        otherCols += "<td>" + sprintf("%s", rowValue[value]) + "</td>\n";
                    }
                    else {
                        otherCols += "<td>" + sprintf("%.10s", rowValue[value]) + "</td>\n";
                    }
                }
            });
            var row = "<tr>"+dateCol+otherCols;
            row += "</tr>\n";
            $("#" + endpoint + "body").append(row);
        });
    });
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
                    } else if(value === "hostname"){
                        otherCols += "<td>" + sprintf("%s", data.result[0][value]) + "</td>\n";
                    }
                    else {
                        otherCols += "<td>" + sprintf("%.10s", data.result[0][value]) + "</td>\n";
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
