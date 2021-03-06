google.load("visualization", "1", {packages:["corechart"]});

/*
google.setOnLoadCallback(initialize);
function initialize() {
}
*/

function drawChart(source_data, title) {
  var data = google.visualization.arrayToDataTable(source_data);

  var options = {
    title: title
    //hAxis: {title: 'Categories'}
  };
  if (title) {
    options.hAxis = {title: title};
  }

  var chart = new google.visualization.ColumnChart(document.getElementById('chart_div'));
  chart.draw(data, options);

  google.visualization.events.addListener(chart, 'select', function() {
    var selection = chart.getSelection()[0];
    console.log(selection);
    console.log(source_data);
    var month = source_data[0][selection.column];
    //var month = source_data[0][1];
    var category = source_data[selection.row][0];
    console.log(month, category);
    var search_url = $('.search a').attr('href');
    search_url = search_url.split('?')[0];
    $('.search a').attr('href', search_url + '?month=' + encodeURIComponent(month) + '&category=' + encodeURIComponent(category));
    $('.search').show();
  });
}

$(function() {

  var soon;
  function submit_soon() {
    $('#sidebar .btn').removeClass('disabled');
    if (soon) {
      clearTimeout(soon);
    }
    soon = setTimeout(function() {
      $('#sidebar').submit();
    }, 1 * 1000);
  }

  $('#sidebar input[type="checkbox"]').change(submit_soon);


  function _serialize_form(form) {
    var parts = {};
    $.each(form.serializeArray(), function(i, each) {
      if (!parts[each.name]) {
        parts[each.name] = [each.value];
      } else {
        parts[each.name].push(each.value);
      }
    });
    var items = [];
    $.each(parts, function(key, values) {
      items.push(key + '=' + values.join(','));
    });
    return items.join('&');
  }

  $('#sidebar').submit(function() {
    // must have at least one checkbox for every group
    var ready = true;
    $('#sidebar .group').each(function() {
      if (!$('input[type="checkbox"]:checked', this).length) {
        ready = false;
      }
    });
    if (ready) {
      $('.not-ready').hide();
      $('#sidebar .loading').show();
      $('.btn', this).addClass('disabled');
      var url = location.pathname + '?' + _serialize_form($(this));
      history.replaceState($(this).serialize(), 'filter', url);
      $.getJSON(url + '&format=json', function(response) {
        if (response.rowcount) {
          $('.too-few-rows').hide();
          $('.unloaded').removeClass('unloaded');
          $('#sidebar .loading').hide();
          drawChart(response.data, response.title);
        } else {
          $('.too-few-rows').show();
        }
      });
    } else {
      $('.not-ready').show();

    }
    return false;
  });

  if ($('#sidebar input:checked').length) {
    $('#sidebar').submit();
  }

  function _toggle($element, to) {
    var container = $element.parents('.group');
    $('input[type="checkbox"]', container).each(function() {
      this.checked = to;
    });
    $('#sidebar').submit();
    return false;
  }

  $('a.toggle-check').click(function() {
    return _toggle($(this), true);
  });

  $('a.toggle-uncheck').click(function() {
    return _toggle($(this), false);
  });

});
