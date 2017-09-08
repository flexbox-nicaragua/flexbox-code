// Copyright 2016 The Flexbox Authors. All rights reserved. 
// Licensed under the open source MIT License, which is in the LICENSE file. 
$.getJSON("test.json",function(data){
    console.debug(data);
    var chart = c3.generate({
        axis: {
                x: {
                    type: 'timeseries',
                    tick: {
                        fit: true,
                        format: '%m/%d'
                    }
                }
        },
        data: {
            xs: {
                'data1': 'x1',
                'data2': 'x2',
            },
            json: {
                x1:data.x1,
                x2:data.x2,
                data1:data.data1,
                data2:data.data2
                            
            }
        }
    });

})