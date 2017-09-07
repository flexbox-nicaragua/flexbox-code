
function readyToDump() {
    insertDump("inside", ["datetime", "inside_temp1", "inside_temp2"]);
    insertDump("ambient",["datetime","ambient_temp","humidity"])
    insertDump("switch", ["datetime", "switch"]);
    insertDump("mfi", ["datetime", "i_rms3", "v_rms3"]);
    insertDump("zwave", ["datetime", "houseAll_Current", "houseAll_Voltage"]);
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
        $.each(data.result, function(i, value) {
            var otherCols = "";
            $.each(value, function(key, value) {
                if(cols.indexOf(key) != -1) {
                    if(key === "datetime") {
                        dateCol = "<td>" + sprintf("%s", value) + "</td>\n";
                    } else {
                        otherCols += "<td>" + sprintf("%.5s", value) + "</td>\n";
                    }
                }
            });
            var row = "<tr>"+dateCol+otherCols;
            row += "</tr>\n";
            $("#" + endpoint + "body").append(row);
        });
    });
}



var otherKeys = {
    'members':['fname'],
    'fname':'File Name'
};
var zipdumpKeys = {
    'members':['timestamp', 'start_date', 'end_date'],
    'short_name':'Name',
    'timestamp':'TS',
    'start_date': 'Start Date',
    'end_date': 'End Date'
};

function readyToServe() {
    initTable('zipdump');
    zdCols = [ 
        zipdumpKeys['timestamp'], zipdumpKeys['start_date'], zipdumpKeys['end_date']
    ];
    addColnames($('#zipdump table'), zdCols);
    initTable('otherfiles');
    addColnames($('#otherfiles table'), [otherKeys['fname']]);
    $.getJSON('backup_dir', populateFiles);
}

function populateFiles(data) {
    var ids = [];
    for (var source in data) {
        ids.push(source);
    }
    ids.sort(function(a,b){
        if (a>b) {
            return -1;
        } else if (a<b){
            return 1;
        }
        return 0;
    });
    ids.forEach( function (source, idx, arr) {
        console.log(source);
        var entry = data[source];
        if (entry.appname === 'zipdump') {
            addFileEntry($('#zipdump table'), zipdumpKeys.members, entry);
        } else if (entry.appname === 'other') {
            addFileEntry($('#otherfiles table'), otherKeys.members, entry);
        }
    });
}

function addFileEntry(table, cols, entry) {
    out = '<tr>';
    $.each(cols, 
    function(i, value) { 
        if (i == 0) {
            dldLink = '<td> <a class=\"btn btn-default\" download=%s_%s href=\"backup_dir?fname=%s\">%s</a></td>';
            cell = sprintf(dldLink, Date.now(), entry['fname'], entry['fname'], entry[value]); 
        } else {
            cell = '<td>' + entry[value] + '</td>';
        }
        out += cell;
    });
    out += '</tr>';
    table.append(out);
}


//For key in fileslist
//if appname:zipdump
//add to zipdump table
//  add short filename as description as well as a download button
//  when downloading add the current time to the filename
//else:
//  add to other table as just a filename
//
