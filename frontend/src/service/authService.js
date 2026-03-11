import api from '@/api/axios';

export default {
    login(data) {
        return api.post('/login', data, { withCredentials: true });
    },

    logout() {
        return api.post('/logout', {}, { withCredentials: true });
    },

    getUserInfo() {
        return api.get('/user', { withCredentials: true });
    }
};
