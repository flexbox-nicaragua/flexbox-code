// Copyright 2016 The Flexbox Authors. All rights reserved. 
// Licensed under the open source MIT License, which is in the LICENSE file. 
$(document).ready(function() {
  $('#dateSelect').pickadate({
    min: new Date(2016,6,13),
    max: true,
  })

  $('#python-image-div').hide();
  var $input = $('#dateSelect').pickadate();
  var picker = $input.pickadate('picker');
  picker.set('select',new Date());
  $('#loadPlot').click(function(){
    $('#python-image-div').show();
    var $input = $('#dateSelect').pickadate();
    var picker = $input.pickadate('picker');
    dateString = picker.get('select','yyyy-mm-dd');
    var date = new Date();
    var number = date.getTime();
    flexboxString = 'flxbxD'+$('#flxbx').val();
    $("#pythonPlotMfi").attr('src', 'images/'+dateString+'/'+flexboxString+'/mfi.png?nocache='+number);
    $("#pythonPlotTemps").attr('src', 'images/'+dateString+'/'+flexboxString+'/temps.png?nocache='+number);
    $("#pythonPlotGrid").attr('src', 'images/'+dateString+'/'+flexboxString+'/grid.png?nocache='+number);
    $("#pythonPlotRelay").attr('src', 'images/'+dateString+'/'+flexboxString+'/relay.png?nocache='+number);
    $("#pythonPlotNetwork").attr('src', 'images/'+dateString+'/'+flexboxString+'/network.png?nocache='+number);
    $("#pythonPlotZwave").attr('src', 'images/'+dateString+'/'+flexboxString+'/zwave.png?nocache='+number);
  })
})



