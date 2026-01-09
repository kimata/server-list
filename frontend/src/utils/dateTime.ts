import dayjs from "dayjs";
import "dayjs/locale/ja";
import relativeTime from "dayjs/plugin/relativeTime";

// Configure dayjs once
dayjs.extend(relativeTime);
dayjs.locale("ja");

export { dayjs };
