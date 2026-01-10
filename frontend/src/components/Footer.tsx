import { useState, useEffect } from 'react';
import { version as reactVersion } from 'react';
import { useApi } from '../hooks/useApi';
import { dayjs } from '../utils/dateTime';
import { GitHubIcon } from './Icon';

interface SysInfo {
    image_build_date: string;
}

const SYSTEM_INFO_POLL = 60000;
const TIME_UPDATE = 60000;

function Footer() {
    const [updateTime, setUpdateTime] = useState(dayjs().format('YYYY年MM月DD日 HH:mm'));
    const buildDate = dayjs(import.meta.env.VITE_BUILD_DATE || new Date().toISOString());
    const { data: sysInfo } = useApi<SysInfo>('/server-list/api/sysinfo', { interval: SYSTEM_INFO_POLL });

    useEffect(() => {
        const interval = setInterval(() => {
            setUpdateTime(dayjs().format('YYYY年MM月DD日 HH:mm'));
        }, TIME_UPDATE);

        return () => clearInterval(interval);
    }, []);

    const getImageBuildDate = () => {
        if (!sysInfo?.image_build_date) return 'Unknown';
        const imageBuildDate = dayjs(sysInfo.image_build_date);
        return `${imageBuildDate.format('YYYY年MM月DD日 HH:mm:ss')} [${imageBuildDate.fromNow()}]`;
    };

    return (
        <div className="ml-auto text-right p-2 mt-4" data-testid="footer">
            <div className="text-base">
                <p className="text-gray-500 mb-0 text-sm">
                    更新日時: {updateTime}
                </p>
                <p className="text-gray-500 mb-0 text-sm">
                    イメージビルド: {getImageBuildDate()}
                </p>
                <p className="text-gray-500 mb-0 text-sm">
                    React ビルド: {buildDate.format('YYYY年MM月DD日 HH:mm:ss')} [{buildDate.fromNow()}]
                </p>
                <p className="text-gray-500 mb-0 text-sm">
                    React バージョン: {reactVersion}
                </p>
                <p className="text-3xl">
                    <a
                        href="https://github.com/kimata/server-list"
                        className="text-gray-400 hover:text-gray-600 transition-colors"
                    >
                        <GitHubIcon className="size-8 inline-block" />
                    </a>
                </p>
            </div>
        </div>
    );
}

export default Footer;
