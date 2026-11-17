(function () {
  "use strict";

  if (typeof Chart === "undefined") return;

  var palette = ["#2876c7", "#48a9a6", "#f0ad4e", "#8d7ac8", "#df7272", "#6c9b68", "#718096"];
  Chart.defaults.font.family = '"Segoe UI", Arial, sans-serif';
  Chart.defaults.color = "#64748b";

  function readJson(id) {
    var element = document.getElementById(id);
    if (!element) return null;
    try {
      return JSON.parse(element.textContent);
    } catch (error) {
      console.error("Could not read chart data from " + id + ".", error);
      return null;
    }
  }

  function chart(id, config) {
    var canvas = document.getElementById(id);
    if (canvas) new Chart(canvas, config);
  }

  function axes(max) {
    return {
      y: {
        beginAtZero: true,
        max: max,
        grid: { color: "#edf1f5" },
        ticks: { precision: 0 }
      },
      x: { grid: { display: false } }
    };
  }

  function horizontalAxes() {
    return {
      x: {
        beginAtZero: true,
        max: 100,
        grid: { color: "#edf1f5" },
        ticks: { precision: 0 }
      },
      y: { grid: { display: false } }
    };
  }

  var classData = readJson("class-chart-data");
  if (classData) {
    chart("subjectChart", {
      type: "bar",
      data: {
        labels: classData.subjects,
        datasets: [{
          label: "Average marks",
          data: classData.averages,
          backgroundColor: "#69a8e3",
          borderRadius: 6,
          barThickness: 18
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        scales: horizontalAxes(),
        plugins: { legend: { display: false } }
      }
    });

    chart("gradeChart", {
      type: "doughnut",
      data: {
        labels: classData.grades,
        datasets: [{
          data: classData.grade_counts,
          backgroundColor: palette,
          borderColor: "#fff",
          borderWidth: 3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        plugins: {
          legend: { position: "bottom" },
          tooltip: {
            callbacks: {
              label: function (context) {
                var count = context.raw || 0;
                return " " + context.label + ": " + count + (count === 1 ? " student" : " students");
              }
            }
          }
        }
      }
    });

    chart("classChart", {
      type: "bar",
      data: {
        labels: classData.student_names,
        datasets: [{
          label: "Percentage",
          data: classData.percentages,
          backgroundColor: classData.passed.map(function (passed) {
            return passed ? "#48a579" : "#df7272";
          }),
          borderRadius: 5,
          barThickness: 17
        }]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        scales: horizontalAxes(),
        plugins: { legend: { display: false } }
      }
    });
  }

  var studentData = readJson("student-chart-data");
  if (studentData) {
    chart("studentChart", {
      type: "bar",
      data: {
        labels: studentData.subjects,
        datasets: [
          { label: "Student marks", data: studentData.marks, backgroundColor: "#2876c7", borderRadius: 5 },
          { label: "Class average", data: studentData.averages, backgroundColor: "#a9c8e5", borderRadius: 5 }
        ]
      },
      options: {
        indexAxis: "y",
        responsive: true,
        maintainAspectRatio: false,
        scales: horizontalAxes()
      }
    });
  }

  var progressData = readJson("progress-chart-data");
  if (progressData) {
    var datasets = [{
      label: "Overall percentage",
      data: progressData.percentage,
      borderColor: "#10243e",
      backgroundColor: "#10243e",
      borderWidth: 3,
      tension: .25
    }];
    progressData.subjects && Object.keys(progressData.subjects).forEach(function (subject, index) {
      datasets.push({
        label: subject,
        data: progressData.subjects[subject],
        borderColor: palette[index % palette.length],
        backgroundColor: palette[index % palette.length],
        borderWidth: 2,
        tension: .25
      });
    });
    chart("progressChart", {
      type: "line",
      data: { labels: progressData.labels, datasets: datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: axes(100),
        interaction: { intersect: false, mode: "index" }
      }
    });
  }
})();
