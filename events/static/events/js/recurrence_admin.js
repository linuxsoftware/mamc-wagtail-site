(function() {
  var RecurrenceWidget;

  RecurrenceWidget = (function() {
    function RecurrenceWidget(widgetId) {
      var ourDiv;
      ourDiv = $("#" + widgetId);
      this.our = ourDiv.find.bind(ourDiv);
      this._init();
      return;
    }

    RecurrenceWidget.prototype._init = function() {
      var freq, showAdvanced;
      showAdvanced = this._hasAdvanced();
      this.our(".ev-show-advanced-cbx").prop("checked", showAdvanced);
      this.our(".ev-advanced-repeat").toggle(showAdvanced);
      freq = this.our(".ev-freq-choice > select").val();
      return this._freqChanged(freq);
    };

    RecurrenceWidget.prototype._hasAdvanced = function() {
      var dayChoice, dtstart, interval, ordChoice, weekday, weekdaysTicked;
      interval = this.our(".ev-interval-num > input").val();
      if (interval && parseInt(interval) > 1) {
        return true;
      }
      weekdaysTicked = this.our(".ev-weekdays :checkbox:checked").map(function() {
        return this.value;
      }).get();
      if (weekdaysTicked.length > 1) {
        return true;
      }
      dtstart = new Date(this.our(".ev-start-date > input").val());
      weekday = (dtstart.getDay() + 6) % 7;
      if (weekdaysTicked.length === 1 && parseInt(weekdaysTicked[0]) !== weekday) {
        return true;
      }
      ordChoice = this.our(".ev-ord-choice > select").val();
      if (parseInt(ordChoice) !== 101) {
        return true;
      }
      dayChoice = this.our(".ev-day-choice > select").val();
      if (parseInt(dayChoice) !== 200) {
        return true;
      }
      return false;
    };

    RecurrenceWidget.prototype._clearAdvanced = function() {
      var dtstart, weekday;
      this.our(".ev-interval-num > input").val(1);
      this.our(".ev-weekdays :checkbox").prop("checked", false);
      dtstart = new Date(this.our(".ev-start-date > input").val());
      weekday = (dtstart.getDay() + 6) % 7;
      this.our(".ev-weekdays :checkbox[value=" + weekday + "]").prop("checked", true);
      this.our(".ev-ord-choice > select").val(101);
      this.our(".ev-day-choice > select").val(200);
      this.our(".ev-month-choice > select").val(dtstart.getMonth() + 1);
    };

    RecurrenceWidget.prototype.enable = function() {
      this._enableShowAdvanced();
      this._enableStartDateChange();
      this._enableFreqChange();
    };

    RecurrenceWidget.prototype._enableShowAdvanced = function() {
      this.our(".ev-show-advanced-cbx").click((function(_this) {
        return function(ev) {
          if ($(ev.target).prop("checked")) {
            _this.our(".ev-advanced-repeat").show();
          } else {
            _this.our(".ev-advanced-repeat").hide();
            _this._clearAdvanced();
          }
          return true;
        };
      })(this));
    };

    RecurrenceWidget.prototype._enableStartDateChange = function() {
      this.our(".ev-start-date > input, .ev-").change((function(_this) {
        return function(ev) {
          var showAdvanced;
          showAdvanced = _this.our(".ev-show-advanced-cbx").prop("checked");
          if (!showAdvanced) {
            _this._clearAdvanced();
          }
          return false;
        };
      })(this));
    };

    RecurrenceWidget.prototype._enableFreqChange = function() {
      this.our(".ev-freq-choice > select").change((function(_this) {
        return function(ev) {
          _this._freqChanged($(ev.target).val());
          _this._clearAdvanced();
          return false;
        };
      })(this));
    };

    RecurrenceWidget.prototype._freqChanged = function(freq) {
      var units, vis;
      vis = [false, false, false];
      units = "";
      switch (parseInt(freq)) {
        case 3:
          vis = [false, false, false];
          units = "Day(s)";
          break;
        case 2:
          vis = [true, false, false];
          units = "Week(s)";
          break;
        case 1:
          vis = [false, true, false];
          units = "Month(s)";
          break;
        case 0:
          vis = [false, true, true];
          units = "Year(s)";
      }
      this.our(".ev-advanced-weekly-repeat").toggle(vis[0]);
      this.our(".ev-advanced-monthly-repeat").toggle(vis[1]);
      this.our(".ev-advanced-yearly-repeat").toggle(vis[2]);
      this.our(".ev-interval-units").text(units);
    };

    return RecurrenceWidget;

  })();

  this.initRecurrenceWidget = function(id) {
    var widget;
    widget = new RecurrenceWidget(id);
    widget.enable();
  };

  this.initExceptionDateChooser = function(id, validDates) {
    var dtpOpts;
    dtpOpts = {
      onGenerate: function(ct) {
        var dd, future, i, len, mm, results, yyyy, yyyymmdd;
        future = new Date();
        future.setDate(future.getDate() + 157);
        future.setDate(1);
        console.log(future);
        if (validDates !== -1 && ct < future) {
          $(this).find('td.xdsoft_date').addClass('xdsoft_disabled');
          results = [];
          for (i = 0, len = validDates.length; i < len; i++) {
            yyyymmdd = validDates[i];
            yyyy = parseInt(yyyymmdd.slice(0, 4));
            mm = parseInt(yyyymmdd.slice(4, 6)) - 1;
            dd = parseInt(yyyymmdd.slice(6, 8));
            results.push($(this).find("td.xdsoft_date[data-year=" + yyyy + "][data-month=" + mm + "][data-date=" + dd + "]").removeClass('xdsoft_disabled'));
          }
          return results;
        }
      },
      closeOnDateSelect: true,
      timepicker: false,
      scrollInput: false,
      format: 'Y-m-d',
      dayOfWeekStart: 0
    };
    if (window.dateTimePickerTranslations) {
      dtpOpts['i18n'] = {
        lang: window.dateTimePickerTranslations
      };
      dtpOpts['lang'] = 'lang';
    }
    return $('#' + id).datetimepicker(dtpOpts);
  };

}).call(this);
