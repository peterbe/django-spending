
$.fn.serializeObject = function() {
  var o = {};
  var a = this.serializeArray();
  $.each(a, function() {
    if (o[this.name] !== undefined) {
      if (!o[this.name].push) {
        o[this.name] = [o[this.name]];
      }
      o[this.name].push(this.value || '');
    } else {
      o[this.name] = this.value || '';
    }
  });
  return o;
};

function update_categories(categories, cat_select) {
  var place = $('option[value=""]', cat_select);
  $.each(categories, function(i, each) {
    $('<option>')
      .val(each)
        .text(each)
          .insertAfter(place);
  });
  if (categories.length) {
    $('input[name="other_category"]')
      .hide();
  }
}

function validate_form($form) {
  var errors = 0;
  // check category
  if (!$('select[name="category"]', $form).val()) {
    $('select[name="category"]', $form)
      .addClass('missing')
        .change(function() {
          $(this).removeClass('missing');
          $('input[name="other_category"]', $form).removeClass('missing');
        });
    errors++;
  } else if ($('select[name="category"]', $form).val() === '_other') {
    if (!$('input[name="other_category"]', $form).val()) {
      $('input[name="other_category"]', $form)
        .addClass('missing')
          .change(function() {
            $(this).removeClass('missing');
          });
      errors++;
    }
  }

  // check amount
  var $amount = $('input[name="amount"]', $form);
  var amount = parseFloat($amount.val().replace(/[^\d-\.]/g, ''));
  if (isNaN(amount)) {
    $amount
      .addClass('missing')
        .change(function() {
          $(this).removeClass('missing');
        });
  }

  // check date
  /*
  var $date = $('input[name="date"]');
  var date = $date.val();

  if (!date) {
    $date
      .addClass('missing')
        .change(function() {
          $(this).removeClass('missing');
        });
  }
  */

  return !errors;
}

function panel_changed(id) {
  if (id === '#signin') {
    // nothing
  }

}

function change_panel(id) {
  $('.content').hide();
  panel_changed(id);
  var $element = $(id);
  if ($element.data('title')) {
    $('.title').text($element.data('title'));
  }
  $element.show();
}

$(function() {

  if (!$('input[name="date"]').val()) {
    var today = new Date(),
      y = today.getFullYear(),
      m = ("0" + (today.getMonth() + 1)).slice(-2),
      d = ("0" + today.getDate()).slice(-2);
    $('input[name="date"]').val('' + y + '-' + m + '-' + d);
  }

  var cat_select = $('select[name="category"]');
  if ($('option', cat_select).length <= 2) {

    $.ajax({
       url:'/categories.json',
      success: function(response) {
        update_categories(response.categories, cat_select);
        localStorage.setItem('spendingcategories', JSON.stringify(response.categories));
      },
      error: function(jqXHR, textStatus, errorThrown) {
        var spendingcategories = localStorage.getItem('spendingcategories');
        if (spendingcategories) {
          update_categories(JSON.parse(spendingcategories), cat_select);
        }
      }
    });
  }

  $('select[name="category"]').change(function() {
    if ($(this).val() === '_other') {
      // Other (specify)...
      $('input[name="other_category"]')
        .show()
        .focus();
      setTimeout(function() {
        $('input[name="other_category"]')[0].focus();
      }, 1 * 1000);
    } else {
      $('input[name="other_category"]')
        .hide();
    }
  });

  $('#home a.button-block').click(function() {
    $('#home form').submit();
    return false;
  });

  $('form.expense-entry').submit(function() {
    var $form = $(this);

    $('.missing', $form).removeClass('missing');

    // do some basic validation
    if (!validate_form($form)) {
      alert("Form data not valid. Check it over.");
      return false;
    }

    var post_data = $form.serializeObject();
    if (post_data.category === '_other') {
      //var index = post_data.indexOf('category');
      delete post_data.category;
    }
    //console.log(post_data);

    $.post(location.href, post_data, function(response) {
      if (response.errors) {
        $.each(response.errors, function(key, message) {
          alert('ERROR ' + key + ': ' + message);
        })
      } else {
        if (response.success_message) {
          var container = $('#home');
          $('p:visible', container).addClass('temphidden').hide();
          $('p.messages', container).text(response.success_message).fadeIn(500);
          setTimeout(function() {
            $('p.messages', container).removeClass('temphidden').hide();
            $('p.temphidden', container).removeClass('temphidden').fadeIn(500);
          }, 10 * 1000);
          document.getElementById('till').play();
        }
        if (response.todays_date) {
          $('input[name="date"]').val(response.todays_date);
        }

        $form[0].reset();
      }
    });
    return false;
  });


  $('#signin a.button-block').click(function() {
    $('#signin form').submit();
    return false;
  });

  $('#signin form').submit(function() {
    var $form = $(this);
    var post_data = $form.serializeObject();
    $.post('/mobile/auth/', post_data, function(response) {
      if (response.username) {
        change_panel('#home');
      }
    });
    return false;
  });

  $('a.panel-change').click(function() {
    var id = $(this).attr('href');
    change_panel(id);
    return false;
  });

  $('#home .username').hide();
  $('#home .offline').show();
  change_panel('#home');

  $.ajax({
     url: '/mobile/auth/',
    cache: false,
    success: function(response) {
      if (response.csrf_token) {
        $('#signin input[name="csrfmiddlewaretoken"]').val(response.csrf_token);
      }
      if (!response.username) {
        change_panel('#signin');
      } else {
        $('#home .notloggedin').hide();
        $('#home .offline').hide();
        change_panel('#home');
        $('#home .username b').text(response.username);
        $('#home .username').fadeIn(500);
      }
    },
    error: function(jqXHR, textStatus, errorThrown) {
      $('#home .notloggedin').hide();
      $('#home .offline').show();
    }
  });
});
