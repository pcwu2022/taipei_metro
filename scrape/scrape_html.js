const transpose = m => m[0].map((x,i) => m.map(x => x[i]));

const timeToInt = time => time === "" ? null : parseInt(time.split(":")[0]) * 60 + parseInt(time.split(":")[1]);

const timeShift = time => time === null ? null : time < 4*60 ? time + 24*60 : time;

const scrape = () => {
    const stationsTable = document.querySelector("#stations");
    const timeTable = document.querySelector("#timetable");

    if (!stationsTable || !timeTable) {
        console.error("Required tables not found in the document.");
        return {};
    }

    const stations = [...stationsTable.children[0].children].map((tr) => tr.textContent.split(" ")[0]);
    const times = [...timeTable.children[0].children].map((tr) => {
        return [...tr.children].map((td) => timeShift(timeToInt(td.textContent)));
    });
    const trainSchedules = transpose(times);
    return { stations, trainSchedules };
}

const downloadFile = (filename, content) => {
    // Create a new Blob object with the content
    const blob = new Blob([content], { type: 'text/plain' });
    
    // Create a temporary link element
    const link = document.createElement("a");
    
    // Set the download attribute with the filename
    link.download = filename;
    
    // Create a URL for the Blob and set it as the href of the link
    link.href = URL.createObjectURL(blob);
    
    // Programmatically click the link to trigger the download
    link.click();
    
    // Clean up by revoking the Object URL
    URL.revokeObjectURL(link.href);
}

const fileName = location.pathname.split("/").reverse()[0].split(".html")[0].replaceAll(",", "").replaceAll("-","_");

const data = scrape();
downloadFile(`${fileName}_schedule.json`, JSON.stringify(data, null, 2));
